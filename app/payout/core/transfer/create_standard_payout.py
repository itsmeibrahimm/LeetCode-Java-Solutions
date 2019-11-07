import re
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from datetime import datetime, timezone
from structlog.stdlib import BoundLogger
from typing import Union, Optional, Dict

from stripe.error import StripeError

from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    StripeCreatePayoutRequest,
    StripeCreateTransferRequest,
)
from app.payout.core.account.utils import (
    get_account_balance,
    get_currency_code,
    get_country_shortname,
)
from app.commons.providers.stripe import stripe_models as models
from app.payout.core.exceptions import PayoutErrorCode, PayoutError
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransfer,
    ManagedAccountTransferUpdate,
    ManagedAccountTransferCreate,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferCreate,
    StripeTransfer,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.models import (
    PayoutAccountId,
    PayoutAmountType,
    PayoutMethodType,
    PayoutTargetType,
    PayoutType,
    AccountType,
    PayoutAccountTargetType,
    StripeTransferSubmissionStatus,
    ManagedAccountTransferStatus,
    StripeErrorCode,
    UNKNOWN_ERROR_STR,
    STRIPE_TRANSFER_FAILED_STATUS,
    TransferId,
)


class CreateStandardPayoutResponse(OperationResponse):
    pass


class CreateStandardPayoutRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.STANDARD
    transfer_id: TransferId
    statement_descriptor: str
    target_id: Optional[str] = None
    target_type: Optional[PayoutTargetType] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


class CreateStandardPayout(
    AsyncOperation[CreateStandardPayoutRequest, CreateStandardPayoutResponse]
):
    """
    Processor to create a standard payout.
    """

    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: CreateStandardPayoutRequest,
        *,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe = stripe

    async def _execute(self) -> CreateStandardPayoutResponse:
        transfer_id = self.request.transfer_id
        self.logger.info(
            "Creating a standard payout.",
            transfer_id=transfer_id,
            payment_account_id=self.request.payout_account_id,
        )
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            payment_account_id=self.request.payout_account_id
        )
        if not payment_account:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID,
                retryable=False,
            )
        if (
            not payment_account.account_type
            == AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT
        ):
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT,
                retryable=False,
            )

        is_transfer_processing = await self.is_processing_or_processed_for_method(
            transfer_id=transfer_id
        )
        if is_transfer_processing:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_PROCESSING,
                retryable=False,
            )

        await self.has_stripe_managed_account(payment_account=payment_account)
        await self.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer_id,
            amount=self.request.amount,
            stripe=self.stripe,
        )
        await self.submit_stripe_transfer(
            transfer_id=transfer_id,
            payment_account=payment_account,
            amount=self.request.amount,
            statement_descriptor=self.request.statement_descriptor,
            target_type=self.request.target_type,
            target_id=self.request.target_id,
            stripe=self.stripe,
        )

        self.logger.info(
            "Successfully created a standard payout.",
            transfer_id=self.request.transfer_id,
            payment_account_id=self.request.payout_account_id,
        )
        return CreateStandardPayoutResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, CreateStandardPayoutResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def is_processing_or_processed_for_method(self, transfer_id: int) -> bool:
        stripe_transfers = await self.stripe_transfer_repo.get_all_ongoing_stripe_transfers_by_transfer_id(
            transfer_id=transfer_id
        )
        return len(stripe_transfers) > 0

    async def has_stripe_managed_account(self, payment_account: PaymentAccount) -> bool:
        """
        Original function name in dsj: check_stripe_account_status_and_update_transfer
        :param payment_account: PaymentAccount to get account_id
        :return: bool, whether there is corresponding sma with given account_id in payment_account
        """
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if stripe_managed_account:
                return True
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID,
            retryable=False,
        )

    async def validate_payment_account_of_managed_account_transfer(
        self,
        payment_account: PaymentAccount,
        managed_account_transfer: Optional[ManagedAccountTransfer],
    ) -> bool:
        """
        Original function name in dsj: check_payment_account_of_managed_account_transfer
        :param payment_account: PaymentAccount, id for validation
        :param managed_account_transfer: ManagedAccountTransfer, optional for payement_account_id validation
        :return:
        """
        if managed_account_transfer and managed_account_transfer.payment_account_id:
            if payment_account.id != managed_account_transfer.payment_account_id:
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.MISMATCHED_TRANSFER_PAYMENT_ACCOUNT,
                    error_message=f"Transfer: {payment_account.id}; Managed Account Transfer: {managed_account_transfer.payment_account_id}",
                    retryable=False,
                )
        return True

    async def get_stripe_account_id(self, payment_account: PaymentAccount) -> str:
        """
        Original function in dsj: get_stripe_account_id_and_type_for_transfer
        :param payment_account: PaymentAccount to get account_id
        :return: given payment_account, find stripe_id of corresponding sma if exists
        """
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if stripe_managed_account:
                return stripe_managed_account.stripe_id
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT,
            retryable=False,
        )

    async def managed_account_balance_check(
        self,
        payment_account: PaymentAccount,
        transfer_id: int,
        amount: int,
        stripe: StripeAsyncClient,
    ):
        """
        Check balance for stripe_managed_account, if it has a managed_account_transfer, update amount if needed
        If it does not have a managed_account_transfer, create one with needed amount
        :param payment_account: PaymentAccout, to check the entity of account
        :param transfer_id: transfer_id, int
        :param amount: amount of the transfer
        :param stripe: StripeAsyncClient
        """
        if payment_account.entity == PayoutAccountTargetType.DASHER:
            amount_still_needed = amount
        else:
            stripe_managed_account = (
                await self.payment_account_repo.get_stripe_managed_account_by_id(
                    payment_account.account_id
                )
                if payment_account.account_id
                else None
            )
            account_balance = await get_account_balance(
                stripe_managed_account=stripe_managed_account, stripe=stripe
            )
            amount_still_needed = amount - account_balance
        managed_account_transfer = await self.managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer_id
        )
        await self.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account,
            managed_account_transfer=managed_account_transfer,
        )
        if amount_still_needed > 0:
            if managed_account_transfer:
                if managed_account_transfer.amount < amount_still_needed:
                    self.logger.info(
                        "Updating amount of the managed account transfer.",
                        managed_account_transfer_id=managed_account_transfer.id,
                        transfer_id=transfer_id,
                        original_amount=managed_account_transfer.amount,
                        new_amount=amount_still_needed,
                    )
                    request = ManagedAccountTransferUpdate(amount=amount_still_needed)
                    await self.managed_account_transfer_repo.update_managed_account_transfer_by_id(
                        managed_account_transfer_id=managed_account_transfer.id,
                        data=request,
                    )
            else:
                self.logger.info(
                    "Creating a managed account transfer",
                    transfer_id=transfer_id,
                    amount=amount_still_needed,
                )
                country_shortname = await get_country_shortname(
                    payment_account=payment_account,
                    payment_account_repository=self.payment_account_repo,
                )
                create_request = ManagedAccountTransferCreate(
                    amount=amount_still_needed,
                    transfer_id=transfer_id,
                    payment_account_id=payment_account.id,
                    currency=get_currency_code(country_shortname=country_shortname)
                    if country_shortname
                    else None,
                )
                await self.managed_account_transfer_repo.create_managed_account_transfer(
                    data=create_request
                )
        else:
            if managed_account_transfer:
                # managed_account_transfer only submit transfer amount greater than 0
                request = ManagedAccountTransferUpdate(amount=0)
                await self.managed_account_transfer_repo.update_managed_account_transfer_by_id(
                    managed_account_transfer_id=managed_account_transfer.id,
                    data=request,
                )

    async def submit_stripe_transfer(
        self,
        transfer_id: int,
        payment_account: PaymentAccount,
        amount: int,
        statement_descriptor: str,
        stripe: StripeAsyncClient,
        target_type: Optional[PayoutTargetType],
        target_id: Optional[str],
    ):
        """
        Aggregation of submit_to_gateway and _submit_stripe_transfer in dsj
        :param transfer_id: transfer_id, int
        :param payment_account: PaymentAccount
        :param amount: int, amount of the transfer
        :param statement_descriptor: str, used to create payout
        :param target_type: dasher or store
        :param target_id: dasher id or store id
        :param stripe: StripeAsyncClient
        """
        try:
            request = StripeTransferCreate(
                transfer_id=transfer_id,
                submission_status=StripeTransferSubmissionStatus.SUBMITTING,
                stripe_status="",
            )
            stripe_transfer = await self.stripe_transfer_repo.create_stripe_transfer(
                data=request
            )

            await self._submit_stripe_transfer(
                stripe_transfer=stripe_transfer,
                payment_account=payment_account,
                amount=amount,
                statement_descriptor=statement_descriptor,
                transfer_id=transfer_id,
                target_type=target_type,
                target_id=target_id,
                stripe=stripe,
            )
        except PayoutError as e:
            retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                transfer_id=transfer_id
            )
            self.logger.info(
                "Submit Stripe Transfer failed",
                transfer_id=transfer_id,
                stripe_transfer_id=retrieved_stripe_transfer.id
                if retrieved_stripe_transfer
                else None,
                error_type=e.error_code,
                error_message=e.error_message,
            )
            raise e

    async def _submit_stripe_transfer(
        self,
        stripe_transfer: StripeTransfer,
        payment_account: PaymentAccount,
        amount: int,
        transfer_id: int,
        statement_descriptor: str,
        stripe: StripeAsyncClient,
        target_type: Optional[PayoutTargetType],
        target_id: Optional[str],
    ):
        """
        Original function in dsj: submit(stripe_transfer)
        """
        if stripe_transfer.stripe_id:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.DUPLICATE_STRIPE_TRANSFER,
                retryable=False,
            )
        stripe_account_id = await self.get_stripe_account_id(
            payment_account=payment_account
        )
        try:
            payout_of_stripe = await self.create_for_managed_account(
                amount=amount,
                transfer_id=transfer_id,
                payment_account=payment_account,
                statement_descriptor=statement_descriptor,
                target_type=target_type,
                target_id=target_id,
                stripe_account_id=stripe_account_id,
                stripe=stripe,
            )
            stripe_bank_account = getattr(payout_of_stripe, "bank_account", None)
            update_request = StripeTransferUpdate(
                country_shortname=await get_country_shortname(
                    payment_account=payment_account,
                    payment_account_repository=self.payment_account_repo,
                ),
                stripe_account_id=stripe_account_id,
                stripe_account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
                stripe_status=payout_of_stripe.status,
                stripe_id=payout_of_stripe.id,
                bank_name=getattr(stripe_bank_account, "bank_name", None),
                bank_last_four=getattr(stripe_bank_account, "last4", None),
                submission_status=StripeTransferSubmissionStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc),
            )
            updated_stripe_transfer = await self.stripe_transfer_repo.update_stripe_transfer_by_id(
                stripe_transfer_id=stripe_transfer.id, data=update_request
            )
            assert updated_stripe_transfer, "failed to update stripe_transfer"
            self.logger.info(
                "Stripe transfer submission succeeded",
                id=updated_stripe_transfer.id,
                stripe_id=updated_stripe_transfer.stripe_id,
                stripe_status=updated_stripe_transfer.stripe_status,
                stripe_bank_name=updated_stripe_transfer.bank_name,
                stripe_bank_last4=updated_stripe_transfer.bank_last_four,
                stripe_request_id=updated_stripe_transfer.stripe_request_id,
            )
        except StripeError as e:
            error_info = e.json_body.get("error", {})
            stripe_error_message = error_info.get("message")
            submission_error_code = error_info.get("code")
            if not submission_error_code:
                submission_error_code = self.extract_failure_code_from_exception_message(
                    stripe_error_message
                )
            update_request = StripeTransferUpdate(
                country_shortname=await get_country_shortname(
                    payment_account=payment_account,
                    payment_account_repository=self.payment_account_repo,
                ),
                stripe_account_id=stripe_account_id,
                stripe_account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
                stripe_status=STRIPE_TRANSFER_FAILED_STATUS,
                stripe_request_id=e.request_id,
                submission_status=(
                    StripeTransferSubmissionStatus.SUBMITTED
                    if e.request_id
                    else StripeTransferSubmissionStatus.FAILED_TO_SUBMIT
                ),
                submission_error_type=error_info.get("type"),
                submission_error_code=submission_error_code,
            )
            updated_stripe_transfer = await self.stripe_transfer_repo.update_stripe_transfer_by_id(
                stripe_transfer_id=stripe_transfer.id, data=update_request
            )
            assert updated_stripe_transfer, "failed to update stripe_transfer"
            self.logger.info(
                "Stripe transfer submission failed",
                id=updated_stripe_transfer.id,
                request_id=updated_stripe_transfer.stripe_request_id,
                submission_status=updated_stripe_transfer.submission_status,
                submission_error_type=updated_stripe_transfer.submission_error_type,
                submission_error_code=updated_stripe_transfer.submission_error_code,
                submission_error_message=stripe_error_message,
            )
            # handle missing external account and payout disallowed first since they requires actions from dx/mx
            if (
                updated_stripe_transfer.submission_error_code
                == StripeErrorCode.NO_EXT_ACCOUNT_IN_CURRENCY
            ):
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.STRIPE_PAYOUT_ACCT_MISSING,
                    retryable=False,
                    error_message=stripe_error_message,
                )
            if (
                updated_stripe_transfer.submission_error_code
                == StripeErrorCode.PAYOUT_NOT_ALLOWED
            ):
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.STRIPE_PAYOUT_DISALLOWED,
                    retryable=False,
                    error_message=stripe_error_message,
                )
            # invalid request error should be treated differently since it's usually due to sma setup issue
            if (
                updated_stripe_transfer.submission_error_type
                == StripeErrorCode.INVALID_REQUEST_ERROR
            ):
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.STRIPE_INVALID_REQUEST_ERROR,
                    retryable=False,
                    error_message=stripe_error_message,
                )
            # other errors are likely system errors
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.STRIPE_SUBMISSION_ERROR,
                retryable=False,
                error_message=stripe_error_message,
            )

    async def create_for_managed_account(
        self,
        amount: int,
        transfer_id: int,
        payment_account: PaymentAccount,
        stripe: StripeAsyncClient,
        stripe_account_id: str,
        statement_descriptor: str,
        target_type: Optional[PayoutTargetType],
        target_id: Optional[str],
    ) -> models.Payout:
        """
        This is the part that actually submits transfer and payout on Stripe platform
        _submit_managed_account_transfer will create transfer on Stripe and transfer money from DD sma to merchant/dasher sma
        If this step failed, exception will be raised and the second step will not be performed
        After _submit_managed_account_transfer is succeed, payout will be created and money will be paid out to corresponding bank_account

        """
        managed_account_transfer = await self.managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer_id
        )
        if not managed_account_transfer:
            self.logger.info(
                "Cannot find managed_account_transfer. Could be SMA balance is enough for payout.",
                transfer_id=transfer_id,
                payment_account_id=payment_account.id,
            )

        if managed_account_transfer and managed_account_transfer.amount > 0:
            await self.submit_managed_account_transfer(
                managed_account_transfer=managed_account_transfer,
                payment_account=payment_account,
                stripe=stripe,
            )

        self.logger.info("Creating a Stripe Payout.", transfer_id=transfer_id)
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=self.payment_account_repo,
        )
        if not country_shortname:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.UNSUPPORTED_COUNTRY,
                retryable=False,
            )
        create_payout_request = StripeCreatePayoutRequest(
            statement_descriptor=statement_descriptor.replace(">", "")
            .replace("<", "")
            .replace("'", "")
            .replace('"', ""),
            metadata=self.get_stripe_transfer_metadata(
                transfer_id=transfer_id,
                payment_account=payment_account,
                target_type=target_type,
                target_id=target_id,
            ),
        )
        currency = get_currency_code(country_shortname)
        return await stripe.create_payout(
            amount=models.Amount(amount),
            currency=models.Currency(currency),
            country=models.CountryCode(country_shortname),
            stripe_account=models.StripeAccountId(stripe_account_id),
            request=create_payout_request,
        )

    async def submit_managed_account_transfer(
        self,
        managed_account_transfer: ManagedAccountTransfer,
        payment_account: PaymentAccount,
        stripe: StripeAsyncClient,
    ):
        """
        Create transfer on Stripe to move money from DD sma to merchant/dasher sma
        :param managed_account_transfer: ManagedAccountTransfer
        :param payment_account: PaymentAccount
        :param stripe: StripeAsyncClient
        """
        if managed_account_transfer.amount <= 0:
            return

        stripe_managed_account = (
            await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if payment_account.account_id
            else None
        )
        if not stripe_managed_account:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID,
                retryable=False,
            )
        stripe_destination_id = stripe_managed_account.stripe_id

        country = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=self.payment_account_repo,
        )

        transfer = await stripe.create_transfer(
            amount=models.Amount(managed_account_transfer.amount),
            currency=models.Currency(managed_account_transfer.currency),
            destination=models.Destination(stripe_destination_id),
            country=models.CountryCode(country),
            request=StripeCreateTransferRequest(),
        )
        update_request = ManagedAccountTransferUpdate(
            stripe_id=transfer.id,
            stripe_status=ManagedAccountTransferStatus.PAID.value,
            submitted_at=datetime.utcnow(),
        )
        await self.managed_account_transfer_repo.update_managed_account_transfer_by_id(
            managed_account_transfer_id=managed_account_transfer.id, data=update_request
        )

    def get_stripe_transfer_metadata(
        self,
        transfer_id: int,
        payment_account: PaymentAccount,
        target_type: Optional[PayoutTargetType],
        target_id: Optional[str],
    ) -> Dict:
        """
        Generate a dict that contains transfer id and payment account info as transfer metadata for stripe api calls.
        Expected keys are transfer_id, account_id, target_id, target_type.
        :rtype: dict
        """
        transfer_metadata: Dict[str, Union[str, int]] = {"transfer_id": transfer_id}
        transfer_metadata["account_id"] = payment_account.id
        if target_type:
            transfer_metadata["target_type"] = target_type
        if target_id:
            transfer_metadata["target_id"] = int(target_id)
        return transfer_metadata

    def extract_failure_code_from_exception_message(
        self, message: Optional[str]
    ) -> str:
        """
        Extracts the failure code from the message.
        :param message: The exception message to scan
        :return: failure code if determined or UNKNOWN_ERROR_STR
        """
        TRANSFER_RELATED_ERROR_MESSAGES = [
            (
                StripeErrorCode.NO_EXT_ACCOUNT_IN_CURRENCY,
                re.compile(
                    "Sorry, you don't have any external accounts in that currency \\((\\w+)\\)"
                ),
            )
        ]
        if message:
            for (failure_code, message_pattern) in TRANSFER_RELATED_ERROR_MESSAGES:
                if message_pattern.match(message):
                    return failure_code
        return UNKNOWN_ERROR_STR

from datetime import datetime, timezone, timedelta
import re
from doordash_python_stats.ddstats import doorstats_global

from starlette.status import HTTP_400_BAD_REQUEST
from stripe.error import StripeError

from app.commons.providers.dsj_client import DSJClient
from app.commons.runtime import runtime
from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional, Dict, List
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
from app.payout.constants import (
    CURRENCY_TO_MAX_TRANSFER_AMOUNT_IN_BASE_UNIT,
    MAX_TRANSFER_AMOUNT_IN_CENTS,
    FF_CHECK_FOR_RECENT_BANK_CHANGE,
    DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK,
    DEFAULT_USER_EMAIL_FOR_SUPERPOWERS,
    ATTEMPTED_COUNT_STAT,
    ATTEMPTED_AMOUNT_STAT,
    transfer_submission_monitoring_stat_name,
    SUCCEEDED_COUNT_STAT,
    SUCCEEDED_AMOUNT_STAT,
)
from app.payout.core.account.utils import (
    get_country_shortname,
    get_currency_code,
    get_account_balance,
)
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.core.transfer.utils import get_target_metadata
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
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
    StripeTransfer,
    StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    TransferUpdate,
    Transfer,
    TransferStatus,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.commons.providers.stripe import stripe_models as models
from app.payout.models import (
    PayoutMethodType,
    TransferStatusCodeType,
    TransferMethodType,
    TRANSFER_METHOD_CHOICES,
    AccountType,
    StripeTransferSubmissionStatus,
    STRIPE_TRANSFER_FAILED_STATUS,
    StripeErrorCode,
    ManagedAccountTransferStatus,
    UNKNOWN_ERROR_STR,
    TRANSFER_ERROR_TYPE_TO_FAILED_STATUS,
    TransferId,
    TRANSFER_METHOD_TO_SUBMIT_FUNCTION,
)


class SubmitTransferResponse(OperationResponse):
    pass


class SubmitTransferRequest(OperationRequest):
    transfer_id: TransferId
    method: Optional[str] = TransferMethodType.STRIPE
    retry: Optional[bool] = False
    submitted_by: Optional[int] = None


class SubmitTransfer(AsyncOperation[SubmitTransferRequest, SubmitTransferResponse]):
    """
    Processor to submit a transfer.
    """

    transfer_repo: TransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    stripe: StripeAsyncClient
    dsj_client: DSJClient

    def __init__(
        self,
        request: SubmitTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        stripe: StripeAsyncClient,
        dsj_client: DSJClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.stripe = stripe
        self.dsj_client = dsj_client

    async def _execute(self) -> SubmitTransferResponse:
        payout_method = self.request.method
        self.logger.info(
            "Executing submit transfer for account",
            transfer_id=self.request.transfer_id,
            method=payout_method,
        )

        transfer_id = self.request.transfer_id
        transfer = await self.transfer_repo.get_transfer_by_id(transfer_id=transfer_id)
        if not transfer:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_NOT_FOUND,
                retryable=False,
            )
        assert (
            transfer.payment_account_id
        ), "there must be a payment_account_id attached with retrieved transfer"
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            payment_account_id=transfer.payment_account_id
        )
        # payment_account should always be valid
        # account_type must be sma since we should not have any Grab or stripe recipient volume going through PS
        if not payment_account:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID,
                retryable=False,
            )

        transactions: List[
            TransactionDBEntity
        ] = await self.transaction_repo.get_transaction_by_transfer_id_without_limit(
            transfer_id=transfer_id
        )
        if transactions:
            transaction_sum = sum(transaction.amount for transaction in transactions)
            diff = abs(transaction_sum - transfer.amount)
            if diff:
                update_request = TransferUpdate(
                    status=TransferStatus.ERROR,
                    status_code=TransferStatusCodeType.ERROR_AMOUNT_MISMATCH,
                )
                await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer_id, data=update_request
                )
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.MISMATCHED_TRANSFER_AMOUNT,
                    retryable=False,
                )
        else:
            update_request = TransferUpdate(
                status=TransferStatus.ERROR,
                status_code=TransferStatusCodeType.ERROR_INVALID_STATE,
            )
            await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer_id, data=update_request
            )
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_INVALID_STATE,
                retryable=False,
            )

        # There is a bug where currency is not set properly; this is a temporary hack to fix it
        if not transfer.currency:
            currency = await get_country_shortname(
                payment_account=payment_account,
                payment_account_repository=self.payment_account_repo,
            )
            self.logger.warn(
                "Transfer currency not set; setting to retrieved currency",
                transfer_id=transfer.id,
                set_to_currency=currency,
            )
            update_request = TransferUpdate(currency=currency)
            transfer = await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer_id, data=update_request
            )
        assert transfer, "transfer must be updated successfully"
        if transfer.deleted_at:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_ALREADY_DELETED,
                retryable=False,
            )
        if not self.request.retry:
            method = payout_method or transfer.method
            if transfer.submitted_at or await self.get_latest_transfer_submission(
                transfer_id=transfer_id, method=method
            ):
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.DUPLICATE_TRANSFER,
                    retryable=False,
                )
        else:
            # Do not attempt to transfer if this is a retry and the payment account doesnt have transfers enabled
            if (
                transfer.status == TransferStatus.ERROR
                and not payment_account.transfers_enabled
            ):
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.TRANSFER_DISABLED_ERROR,
                    retryable=False,
                )
        assert (
            payout_method
        ), "payout_method must be valid since we have assign default value to it"
        if transfer.amount == 0 or payout_method in (
            TransferMethodType.DOORDASH_PAY,
            TransferMethodType.COD_INVOICE,
        ):
            await self.handle_dummy_transfer(
                transfer_id=transfer_id, method=payout_method
            )
            return SubmitTransferResponse()
        await self.transfer_amount_check(
            transfer=transfer, submitted_by=self.request.submitted_by
        )
        assert payout_method in [choice[0] for choice in TRANSFER_METHOD_CHOICES]
        is_transfer_processing = await self.is_processing_or_processed_for_method(
            transfer_id=transfer_id, method=payout_method
        )
        if is_transfer_processing:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_PROCESSING,
                retryable=False,
            )
        if payout_method == TransferMethodType.STRIPE:
            await self.has_stripe_managed_account(
                payment_account=payment_account, transfer_id=transfer_id
            )
            await self.managed_account_balance_check(
                transfer_id=transfer_id,
                payment_account=payment_account,
                amount=transfer.amount,
            )
        await self.submit_stripe_transfer(
            transfer_id=transfer_id,
            payment_account=payment_account,
            method=payout_method,
            amount=transfer.amount,
            submitted_by=self.request.submitted_by,
        )
        self.logger.info(
            "Finished executing submit transfer for account",
            payment_account_id=payment_account.id,
            transfer_id=transfer_id,
        )
        return SubmitTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, SubmitTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def handle_dummy_transfer(self, transfer_id: int, method: str):
        """
        Handle dummy transfer by setting submitted_at and marking transfer as paid
        Only use the function if the transfer's amount is 0 or transfer is an employee payout
        :param: method, PayoutMethodType
        :rtype: bool
        """
        try:
            update_request = TransferUpdate(
                method=method,
                submitted_at=datetime.utcnow(),
                status=TransferStatus.PAID,
                status_code=None,
            )
            await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer_id, data=update_request
            )
            return True
        except Exception as e:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.DUMMY_TRANSFER_CREATION_FAILED,
                retryable=False,
                error_message=f"Failed to create dummy transfer because: {e}",
            )

    async def get_latest_transfer_submission(
        self, transfer_id: int, method: str
    ) -> Optional[StripeTransfer]:
        if method == TransferMethodType.STRIPE:
            return await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                transfer_id=transfer_id
            )
        return None

    async def transfer_amount_check(
        self, transfer: Transfer, submitted_by: Optional[int]
    ):
        assert transfer.currency, "currency should be set before calling this function"
        assert (
            transfer.payment_account_id
        ), "payment_account_id should be checked before calling this function, cannot be None"

        default_max_amount = CURRENCY_TO_MAX_TRANSFER_AMOUNT_IN_BASE_UNIT.get(
            transfer.currency, MAX_TRANSFER_AMOUNT_IN_CENTS  # default to USD
        )
        account_limitations = runtime.get_json(
            "payout/feature-flags/payment_account_transfer_limit_overrides.json", {}
        )
        max_amount_dict = account_limitations.get(
            transfer.payment_account_id, None
        ) or runtime.get_int("payout/feature-flags/default_transfer_max.int", {})
        max_amount = max_amount_dict.get(transfer.currency, default_max_amount)
        # check if transfer amount exceeds max amount AND there was a recent bank change
        should_error_on_large_amt = transfer.amount >= max_amount

        if runtime.get_bool(FF_CHECK_FOR_RECENT_BANK_CHANGE, False):
            if should_error_on_large_amt:
                days = runtime.get_int(
                    DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK, default=14
                )
                most_recent_updated_bank_account = await self.payment_account_edit_history_repo.get_most_recent_bank_update(
                    payment_account_id=transfer.payment_account_id,
                    within_last_timedelta=timedelta(days=days),
                )
                should_error_on_large_amt = (
                    True if most_recent_updated_bank_account else False
                )
        if should_error_on_large_amt:
            user_list = []
            if submitted_by:
                user_list.append(submitted_by)
            if transfer.created_by_id:
                user_list.append(transfer.created_by_id)
            has_payment_permission = self.does_user_have_payments_superpowers(
                user_list=user_list,
                runtime_list_name="payout/feature-flags/transfer_amount_limitation_admins.str",
            )
            if not has_payment_permission:
                update_request = TransferUpdate(
                    status=TransferStatus.ERROR,
                    status_code=TransferStatusCodeType.ERROR_AMOUNT_LIMIT_EXCEEDED,
                )
                await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer.id, data=update_request
                )
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.TRANSFER_AMOUNT_OVER_LIMIT,
                    retryable=False,
                )

        if transfer.amount < 0:
            update_request = TransferUpdate(
                status=TransferStatus.ERROR,
                status_code=TransferStatusCodeType.ERROR_AMOUNT_LIMIT_EXCEEDED,
            )
            await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer.id, data=update_request
            )
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_AMOUNT_NEGATIVE,
                retryable=False,
            )

    async def is_processing_or_processed_for_method(
        self, transfer_id: int, method: str
    ) -> bool:
        if method == PayoutMethodType.STRIPE:
            stripe_transfers = await self.stripe_transfer_repo.get_all_ongoing_stripe_transfers_by_transfer_id(
                transfer_id=transfer_id
            )
            return len(stripe_transfers) > 0

        self.logger.warning(
            "Could not check if transfer is processing",
            transfer_id=transfer_id,
            method=method,
        )
        return False

    async def has_stripe_managed_account(
        self, payment_account: PaymentAccount, transfer_id: int
    ) -> bool:
        """
        Original function name in dsj: check_stripe_account_status_and_update_transfer
        :param payment_account: PaymentAccount to get account_id
        :param transfer_id: int, if there is no
        :return: bool, whether there is corresponding sma with given account_id in payment_account, if not, update transfer
        """
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if stripe_managed_account:
                return True
        update_request = TransferUpdate(
            status=TransferStatus.FAILED,
            status_code=TransferStatusCodeType.ERROR_NO_GATEWAY_ACCOUNT,
        )
        await self.transfer_repo.update_transfer_by_id(
            transfer_id=transfer_id, data=update_request
        )
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID,
            retryable=False,
        )

    async def managed_account_balance_check(
        self, payment_account: PaymentAccount, transfer_id: int, amount: int
    ):
        """
        Check balance for stripe_managed_account, if it has a managed_account_transfer, update amount if needed
        If it does not have a managed_account_transfer, create one with needed amount
        :param payment_account: PaymentAccount, to check the entity of account
        :param transfer_id: transfer_id, int
        :param amount: amount of the transfer
        """
        stripe_managed_account = (
            await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if payment_account.account_id
            else None
        )
        account_balance = await get_account_balance(
            stripe_managed_account=stripe_managed_account, stripe=self.stripe
        )
        amount_still_needed = amount - account_balance
        managed_account_transfer = await self.managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer_id
        )
        await self.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account,
            managed_account_transfer=managed_account_transfer,
            transfer_id=transfer_id,
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

    async def validate_payment_account_of_managed_account_transfer(
        self,
        payment_account: PaymentAccount,
        transfer_id: int,
        managed_account_transfer: Optional[ManagedAccountTransfer],
    ) -> bool:
        """
        Original function name in dsj: check_payment_account_of_managed_account_transfer
        :param payment_account: PaymentAccount, id for validation
        :param transfer_id: int
        :param managed_account_transfer: ManagedAccountTransfer, optional for payement_account_id validation
        :return: bool, whether the payment_account is valid, if not, update transfer and raise exception
        """
        if managed_account_transfer and managed_account_transfer.payment_account_id:
            if payment_account.id != managed_account_transfer.payment_account_id:
                update_request = TransferUpdate(
                    status=TransferStatus.ERROR,
                    status_code=TransferStatusCodeType.ERROR_ACCOUNT_ID_MISMATCH,
                )
                await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer_id, data=update_request
                )
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.MISMATCHED_TRANSFER_PAYMENT_ACCOUNT,
                    error_message=f"Transfer: {payment_account.id}; Managed Account Transfer: {managed_account_transfer.payment_account_id}",
                    retryable=False,
                )
        return True

    async def submit_stripe_transfer(
        self,
        transfer_id: int,
        payment_account: PaymentAccount,
        amount: int,
        method: str,
        submitted_by: Optional[int],
    ):
        """
        Aggregation of submit_to_gateway and _submit_stripe_transfer in dsj
        :param transfer_id: transfer_id, int
        :param payment_account: PaymentAccount
        :param amount: int, amount of the transfer
        :param method: str, transfer method type
        :param submitted_by: id of the user that triggered submit_transfer
        """
        submit_function_name = TRANSFER_METHOD_TO_SUBMIT_FUNCTION.get(
            method, "_submit_stripe_transfer"
        )
        self.logger.info(
            "submitting transfer with function",
            transfer_id=transfer_id,
            submit_function_name=submit_function_name,
        )
        if submit_function_name:
            update_request = TransferUpdate(
                status_code=None, should_retry_on_failure=False, method=method
            )
            updated_transfer = await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer_id, data=update_request
            )
            assert updated_transfer, "updated should success and transfer must exist"
            await self.record_transfer_submission_monitoring_stat(
                transfer=updated_transfer,
                count_stat_name=ATTEMPTED_COUNT_STAT,
                amount_stat_name=ATTEMPTED_AMOUNT_STAT,
            )
            if submit_function_name == TRANSFER_METHOD_TO_SUBMIT_FUNCTION.get(
                TransferMethodType.CHECK
            ):
                await self._submit_check_transfer(
                    transfer_id=transfer_id, submitted_by=submitted_by
                )
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
                    transfer_id=transfer_id,
                )
                update_request = TransferUpdate(
                    submitted_at=datetime.now(timezone.utc),
                    submitted_by_id=submitted_by,
                )
                updated_succeed_transfer = await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer_id, data=update_request
                )
                assert (
                    updated_succeed_transfer
                ), "update should succeed and transfer must exist"
                if (
                    updated_succeed_transfer.status
                    not in TransferStatus.failed_statuses()
                ):
                    await self.record_transfer_submission_monitoring_stat(
                        transfer=updated_succeed_transfer,
                        count_stat_name=SUCCEEDED_COUNT_STAT,
                        amount_stat_name=SUCCEEDED_AMOUNT_STAT,
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
                if e.error_code in TRANSFER_ERROR_TYPE_TO_FAILED_STATUS:
                    update_request = TransferUpdate(
                        status=TransferStatus.FAILED,
                        status_code=e.error_code,
                        submitted_at=datetime.utcnow(),
                        submitted_by_id=submitted_by,
                    )
                    await self.transfer_repo.update_transfer_by_id(
                        transfer_id=transfer_id, data=update_request
                    )
                else:
                    update_request = TransferUpdate(
                        status=TransferStatus.ERROR,
                        status_code=TransferStatusCodeType.ERROR_SUBMISSION,
                    )
                    await self.transfer_repo.update_transfer_by_id(
                        transfer_id=transfer_id, data=update_request
                    )
                raise e
            except Exception as e:
                retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                    transfer_id=transfer_id
                )
                self.logger.exception(
                    "Submit Stripe Transfer got an exception",
                    transfer_id=transfer_id,
                    stripe_transfer_id=retrieved_stripe_transfer.id
                    if retrieved_stripe_transfer
                    else None,
                    error_message=e,
                )
                update_request = TransferUpdate(
                    status=TransferStatus.ERROR,
                    status_code=TransferStatusCodeType.UNKNOWN_ERROR,
                )
                await self.transfer_repo.update_transfer_by_id(
                    transfer_id=transfer_id, data=update_request
                )
                raise e

    async def record_transfer_submission_monitoring_stat(
        self, transfer: Transfer, count_stat_name: str, amount_stat_name: str
    ):
        """
        Stat of transfer submission
        :param transfer: transfer, either to be submitted or already submitted
        :param count_stat_name: string, stat name for count metric
        :param amount_stat_name: string, stat name for amount metric
        :return:
        """
        if transfer.payment_account_id:
            payment_account = await self.payment_account_repo.get_payment_account_by_id(
                payment_account_id=transfer.payment_account_id
            )
            if not payment_account or not payment_account.entity:
                entity = "without-payment-account"
            else:
                entity = payment_account.entity

            submission_metric = transfer_submission_monitoring_stat_name(
                entity=entity, stat_name=count_stat_name
            )
            amount_metric = transfer_submission_monitoring_stat_name(
                entity=entity, stat_name=amount_stat_name
            )
            doorstats_global.incr(submission_metric)
            doorstats_global.incr(amount_metric, transfer.amount)

    async def _submit_stripe_transfer(
        self,
        stripe_transfer: StripeTransfer,
        payment_account: PaymentAccount,
        amount: int,
        transfer_id: int,
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
        if (
            not payment_account.account_type
            == AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT
        ):
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT,
                retryable=False,
            )
        try:
            payout_of_stripe = await self.create_for_managed_account(
                amount=amount,
                transfer_id=transfer_id,
                payment_account=payment_account,
                stripe_account_id=stripe_account_id,
            )
            stripe_bank_account = getattr(payout_of_stripe, "bank_account", None)
            update_stripe_transfer_request = StripeTransferUpdate(
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
                stripe_transfer_id=stripe_transfer.id,
                data=update_stripe_transfer_request,
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
            update_transfer_request = TransferUpdate(
                status=TransferStatus.PENDING, status_code=None
            )
            await self.transfer_repo.update_transfer_by_id(
                transfer_id=transfer_id, data=update_transfer_request
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

    async def _submit_check_transfer(
        self, transfer_id: int, submitted_by: Optional[int]
    ):
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer_id
        )
        assert retrieved_transfer, "given transfer_id must be valid"

        user_list = []
        if submitted_by:
            user_list.append(submitted_by)
        if retrieved_transfer.created_by_id:
            user_list.append(retrieved_transfer.created_by_id)

        has_payment_permission = self.does_user_have_payments_superpowers(
            user_list=user_list,
            runtime_list_name="payout/feature-flags/transfer_amount_limitation_admins.str",
        )
        if not has_payment_permission:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_PERMISSION_ERROR,
                retryable=False,
            )
        update_request = TransferUpdate(
            status_code=None,
            status=TransferStatus.PAID,
            submitted_at=datetime.now(timezone.utc),
            submitted_by=submitted_by,
        )
        await self.transfer_repo.update_transfer_by_id(
            transfer_id=transfer_id, data=update_request
        )

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

    async def create_for_managed_account(
        self,
        amount: int,
        transfer_id: int,
        payment_account: PaymentAccount,
        stripe_account_id: str,
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
        target_type, target_id, statement_descriptor, target_biz_id = await get_target_metadata(
            payment_account_id=payment_account.id, dsj_client=self.dsj_client
        )

        create_payout_request = StripeCreatePayoutRequest(
            statement_descriptor=statement_descriptor.replace(">", "")
            .replace("<", "")
            .replace("'", "")
            .replace('"', "")
            if statement_descriptor
            else "",
            metadata=self.get_stripe_transfer_metadata(
                transfer_id=transfer_id,
                payment_account=payment_account,
                target_type=target_type,
                target_id=target_id,
            ),
        )
        currency = get_currency_code(country_shortname)
        return await self.stripe.create_payout(
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
    ):
        """
        Create transfer on Stripe to move money from DD sma to merchant/dasher sma
        :param managed_account_transfer: ManagedAccountTransfer
        :param payment_account: PaymentAccount
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

        transfer = await self.stripe.create_transfer(
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
        target_type: Optional[str],
        target_id: Optional[int],
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
            transfer_metadata["target_id"] = target_id
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

    def does_user_have_payments_superpowers(
        self, user_list: List[int], runtime_list_name: str
    ):
        """
        Check if the user is admin to submit transfer. Instead of accessing User table like in dsj,
        use user_id and cast str read from runtime to int directly
        :param user_list: List of users that submit/create the transfer
        :param runtime_list_name: name of the runtime that to retrieve, runtime will contain a string of ids
        :return:
        """
        has_super_power = False
        if user_list and runtime_list_name:
            runtime_user_id_str = runtime.get_str(
                runtime_list_name, DEFAULT_USER_EMAIL_FOR_SUPERPOWERS
            )
            runtime_user_id_list = [
                int(user_id.strip()) for user_id in runtime_user_id_str.split(",")
            ]
            has_super_power = len(runtime_user_id_list) > 0 and any(
                user_id in runtime_user_id_list for user_id in user_list
            )
        return has_super_power

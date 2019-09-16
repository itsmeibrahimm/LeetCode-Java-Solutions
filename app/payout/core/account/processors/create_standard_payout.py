import re
from typing import Union, Optional, Tuple

from app.commons.context.logger import Log
from app.commons.core.errors import PaymentError, DEFAULT_INTERNAL_ERROR
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.exceptions import PayoutErrorCode, PayoutError
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransfer,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferCreate
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.types import (
    PayoutAmountType,
    PayoutType,
    PayoutMethodType,
    PayoutAccountId,
    PayoutTargetType,
    AccountType,
)


class CreateStandardPayoutResponse(OperationResponse):
    pass


class CreateStandardPayoutRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.STANDARD
    target_id: Optional[str] = None
    target_type: Optional[PayoutTargetType] = None
    transfer_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


class CreateStandardPayout(
    AsyncOperation[CreateStandardPayoutRequest, CreateStandardPayoutResponse]
):
    """
    Processor to create a standard payout.
    """

    stripe_transfer_repo: StripeTransferRepositoryInterface

    def __init__(
        self,
        request: CreateStandardPayoutRequest,
        *,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_transfer_repo = stripe_transfer_repo

    async def _execute(self) -> CreateStandardPayoutResponse:
        self.logger.info(f"CreateStandardPayout")
        stripe_transfer_create = StripeTransferCreate(
            transfer_id=self.request.transfer_id, stripe_status=""
        )
        stripe_transfer = await self.stripe_transfer_repo.create_stripe_transfer(
            stripe_transfer_create
        )
        self.logger.info(
            f"Created a stripe transfer for StandardPayout. stripe_transfer.id: {stripe_transfer.id}"
        )
        return CreateStandardPayoutResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentError, CreateStandardPayoutResponse]:
        # TODO write actual exception handling
        raise DEFAULT_INTERNAL_ERROR

    async def is_processing_or_processed_for_method(self, transfer_id: int) -> bool:
        stripe_transfers = await self.stripe_transfer_repo.get_all_ongoing_stripe_transfers_by_transfer_id(
            transfer_id=transfer_id
        )
        return len(stripe_transfers) > 0

    async def has_stripe_managed_account(
        self,
        payment_account: Optional[PaymentAccount],
        payment_account_repository: PaymentAccountRepository,
    ) -> bool:
        """
        Original function name in dsj: check_stripe_account_status_and_update_transfer
        :param payment_account: PaymentAccount to get account_id
        :param payment_account_repository: PaymentAccountRepository
        :return: bool, whether there is corresponding sma with given account_id in payment_account
        """
        if payment_account and payment_account.account_id:
            stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            if stripe_managed_account:
                return True
        raise PayoutError(
            error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID, retryable=False
        )

    async def validate_payment_account_of_managed_account_transfer(
        self,
        payment_account: Optional[PaymentAccount],
        managed_account_transfer: Optional[ManagedAccountTransfer],
    ) -> bool:
        """
        Original function name in dsj: check_payment_account_of_managed_account_transfer
        :param payment_account: PaymentAccount, id for validation
        :param managed_account_transfer: ManagedAccountTransfer, optional for payement_account_id validation
        :return:
        """
        if (
            payment_account
            and managed_account_transfer
            and managed_account_transfer.payment_account_id
        ):
            if payment_account.id != managed_account_transfer.payment_account_id:
                raise PayoutError(
                    error_code=PayoutErrorCode.MISMATCHED_TRANSFER_PAYMENT_ACCOUNT,
                    error_message=f"Transfer: {payment_account.id}; Managed Account Transfer: {managed_account_transfer.payment_account_id}",
                    retryable=False,
                )
        return True

    async def get_stripe_account_id_and_payment_account_type(
        self,
        payment_account: PaymentAccount,
        payment_account_repository: PaymentAccountRepository,
    ) -> Tuple[Optional[str], Optional[AccountType]]:
        """
        Original function in dsj: get_stripe_account_id_and_type_for_transfer
        :param payment_account: PaymentAccount to get account_id
        :param payment_account_repository: PaymentAccountRepository
        :return: given payment_account, find stripe_id of corresponding sma and payment_account account_type
        """
        # check account_type before calls this to make sure only SMA can be passed in
        # todo: this can be refactored after stripe_transfer.submit() is added
        stripe_managed_account = None
        if payment_account and payment_account.account_id:
            stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
        return (
            stripe_managed_account.stripe_id if stripe_managed_account else None,
            payment_account.account_type if payment_account else None,
        )

    def extract_failure_code_from_exception_message(
        self, message: Optional[str]
    ) -> str:
        """
        Extracts the failure code from the message.
        :param message: The exception message to scan
        :return: failure code if determined or UNKNOWN_ERROR_STR
        """
        # todo: somehow figure out all those dsj error codes and types and usages then move them together to somewhere
        NO_EXT_ACCOUNT_IN_CURRENCY = "no_external_account_in_currency"
        UNKNOWN_ERROR_STR = "err"
        TRANSFER_RELATED_ERROR_MESSAGES = [
            (
                NO_EXT_ACCOUNT_IN_CURRENCY,
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

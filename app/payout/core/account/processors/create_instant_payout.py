import uuid
from datetime import datetime
from typing import Optional, Union

from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.types import CountryCode
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransfer,
    StripeManagedAccountTransferCreate,
)
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.types import (
    PayoutAccountId,
    PayoutAmountType,
    PayoutMethodType,
    PayoutType,
)


class CreateInstantPayoutResponse(OperationResponse):
    pass


class CreateInstantPayoutRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.INSTANT
    payout_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


def _gen_token():
    return str(uuid.uuid4())


def _get_stripe_platform_account_id(country):
    """
    Returns the stripe platform account id for a country

    :param country: str
    :return: value of DoorDash Stripe platform account id
    :rtype: str
    """
    stripe_platform_account_dict = {
        CountryCode.CA: "acct_16qVpAAFJYNIHuof",
        CountryCode.US: "acct_1xmerw8hWoEwIJg23PRk",
        CountryCode.AU: "acct_1EVmnIBKMMeR8JVH",
    }
    if country in stripe_platform_account_dict:
        return stripe_platform_account_dict[country]
    raise PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_code=PayoutErrorCode.UNHANDLED_COUNTRY,
        retryable=False,
    )


class CreateInstantPayout(
    AsyncOperation[CreateInstantPayoutRequest, CreateInstantPayoutResponse]
):
    """
    Processor to create a instant payout.
    """

    stripe_payout_request_repo: StripePayoutRequestRepositoryInterface

    def __init__(
        self,
        request: CreateInstantPayoutRequest,
        *,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepositoryInterface,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo

    async def _execute(self) -> CreateInstantPayoutResponse:
        self.logger.info(f"CreatedInstantPayout")
        now = datetime.utcnow()
        # TODO: StripePayoutRequestCreate should enforce required columns
        stripe_payout_request_create = StripePayoutRequestCreate(
            payout_id=self.request.payout_id,
            idempotency_key=str(uuid.uuid4()),
            payout_method_id=1,
            created_at=now,
            updated_at=now,
            status="new",
        )
        stripe_payout_request = await self.stripe_payout_request_repo.create_stripe_payout_request(
            stripe_payout_request_create
        )
        self.logger.info(
            f"Created a stripe payout request for InstantPayout. stripe_payout_request.id: {stripe_payout_request.id}"
        )
        return CreateInstantPayoutResponse()

    def _handle_exception(
        self, dep_exec: Exception
    ) -> Union[PaymentException, CreateInstantPayoutResponse]:
        # TODO write actual exception handling
        raise DEFAULT_INTERNAL_EXCEPTION

    async def create_sma_transfer_with_amount(
        self, payment_account: Optional[PaymentAccount], amount: int
    ) -> Optional[StripeManagedAccountTransfer]:
        """Create StripeManagedAccountTransfer with given amount.

        Create StripeManagedAccountTransfer record with the given amount for Fast Payout. The amount should be
        positive value. StripeManagedAccountTransfer is only used for Dasher's FastPay. The equivalent entity for weekly
        pay is ManagedAccountTransfer.

        :param payment_account: Dasher's payment account
        :param amount: StripeManagedAccountTransfer amount
        :return: stripe managed account transfer
        """
        if payment_account and payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            # stripe managed account must be fully setup
            if not stripe_managed_account:
                raise PayoutError(
                    http_status_code=HTTP_400_BAD_REQUEST,
                    error_code=PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT,
                    retryable=False,
                )

            sma_stripe_id = stripe_managed_account.stripe_id
            country = stripe_managed_account.country_shortname
            data = StripeManagedAccountTransferCreate(
                amount=amount,
                from_stripe_account_id=_get_stripe_platform_account_id(country),
                to_stripe_account_id=sma_stripe_id,
                token=_gen_token(),
            )
            sma_transfer = await self.stripe_managed_account_transfer_repo.create_stripe_managed_account_transfer(
                data
            )
            return sma_transfer
        raise PayoutError(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID,
            retryable=False,
        )

    # Todo: stripe managed account transfer submission

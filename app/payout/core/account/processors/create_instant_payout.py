import uuid
from datetime import datetime
from typing import Optional, Union

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from stripe.error import APIConnectionError, StripeError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import Transfer
from app.commons.types import CountryCode
from app.payout.core.account.utils import get_account_balance
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
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
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
    payout_card_id: int
    payout_stripe_card_id: str
    payout_idempotency_key: str
    payout_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


def _gen_token():
    return str(uuid.uuid4())


def _get_currency_code(country):
    # Will change to Yu's util function once her changes get merged
    currency_code_dict = {
        "US": "USD",
        "CA": "CAD",
        "United States": "USD",
        "Canada": "CAD",
        "Indonesia": "IDR",
        "ID": "IDR",
        "SG": "SGD",
        "MY": "MYR",
        "JP": "JPY",
        "AU": "AUD",
    }
    if country in currency_code_dict:
        return currency_code_dict[country]
    raise PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_code=PayoutErrorCode.UNHANDLED_COUNTRY,
        retryable=False,
    )


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
        stripe_async_client: StripeAsyncClient,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.stripe_async_client = stripe_async_client

    async def _execute(self) -> CreateInstantPayoutResponse:
        self.logger.info(f"CreatedInstantPayout")

        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payment_account or not payment_account.account_id:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID,
                retryable=False,
            )

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

        # Create Stripe managed account and Stripe transfers
        await self.create_sma_and_stripe_transfer(
            stripe_managed_account=stripe_managed_account
        )

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

    async def create_sma_and_stripe_transfer(
        self, stripe_managed_account: StripeManagedAccount
    ):
        payout_amount = self.request.amount
        account_balance = await get_account_balance(
            stripe_managed_account=stripe_managed_account,
            stripe=self.stripe_async_client,
        )
        amount_needed = payout_amount - account_balance

        if amount_needed > 0:
            sma_transfer = await self.create_sma_transfer_with_amount(
                stripe_managed_account=stripe_managed_account, amount=amount_needed
            )

            await self.create_stripe_transfer(
                stripe_managed_account=stripe_managed_account, sma_transfer=sma_transfer
            )

    async def create_sma_transfer_with_amount(
        self, stripe_managed_account: StripeManagedAccount, amount: int
    ) -> StripeManagedAccountTransfer:
        """Create StripeManagedAccountTransfer with given amount.

        Create StripeManagedAccountTransfer record with the given amount for Fast Payout. The amount should be
        positive value. StripeManagedAccountTransfer is only used for Dasher's FastPay. The equivalent entity for weekly
        pay is ManagedAccountTransfer.

        :param stripe_managed_account: StripeManagedAccount
        :param amount: StripeManagedAccountTransfer amount
        :return: stripe managed account transfer
        """
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

    async def create_stripe_transfer(
        self,
        stripe_managed_account: StripeManagedAccount,
        sma_transfer: StripeManagedAccountTransfer,
    ) -> Transfer:
        """Submit stripe transfer.

        Call stripe to submit SMA transfer.

        :param stripe_managed_account: StripeManagedAccount
        :param sma_transfer: stripe managed account transfer record
        :return: None
        """
        """ The origin logic is from DSJ _submit_transfer in fast_payouts """
        try:
            response = await self.stripe_async_client.create_transfer(
                amount=models.Amount(sma_transfer.amount),
                currency=models.Currency(
                    _get_currency_code(stripe_managed_account.country_shortname)
                ),
                destination=models.Destination(sma_transfer.to_stripe_account_id),
                country=models.CountryCode(stripe_managed_account.country_shortname),
                request=models.CreateTransfer(),
            )
            self.logger.info(
                f"[Fast Pay Local Creation] succeed to submit a sma transfer. sma_transfer.id: {sma_transfer.id}"
            )
            return response
        except APIConnectionError:
            raise PayoutError(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=PayoutErrorCode.API_CONNECTION_ERROR,
                retryable=False,
            )
        # Todo: would update the error_code with Yu's merge for Stripe submission error
        except StripeError:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.API_CONNECTION_ERROR,
                retryable=False,
            )
        except Exception:
            # Note: we don't know if this transfer succeeded or not, so we assume it didn't and dont
            # persist the request. Re-attempts will reuse the same idempotency key.
            raise PayoutError(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=PayoutErrorCode.OTHER_ERROR,
                retryable=False,
            )

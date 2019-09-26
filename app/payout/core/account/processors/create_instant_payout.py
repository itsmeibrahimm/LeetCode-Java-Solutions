import uuid
from datetime import datetime
from structlog.stdlib import BoundLogger
from typing import Optional, Union

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from stripe.error import APIConnectionError, StripeError, RateLimitError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import Transfer
from app.commons.types import CountryCode
from app.payout.core.account.utils import get_account_balance, get_currency_code
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransfer,
    StripeManagedAccountTransferCreate,
)
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequest,
    StripePayoutRequestCreate,
    StripePayoutRequestUpdate,
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
from app.payout.types import StripePayoutStatus


class CreateInstantPayoutResponse(OperationResponse):
    pass


class CreateInstantPayoutRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.INSTANT
    payout_card_id: int
    payout_stripe_card_id: str
    payout_id: str
    payout_idempotency_key: str
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


DEFAULT_STATEMENT_DESCRIPTOR = "Doordash, Inc. FastPay"


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
        error_code=PayoutErrorCode.UNSUPPORTED_COUNTRY,
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
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.stripe_async_client = stripe_async_client

    async def _execute(self) -> CreateInstantPayoutResponse:
        self.logger.info(f"CreatedInstantPayout")

        payout_account_id = self.request.payout_account_id
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            payout_account_id
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

        payout_id = int(self.request.payout_id)
        payout_idempotency_key = self.request.payout_idempotency_key
        payout_method_id = self.request.payout_card_id
        stripe_account_id = stripe_managed_account.stripe_id
        country = models.CountryCode(stripe_managed_account.country_shortname)
        payout_amount = self.request.amount
        request = {
            "country": country,
            "stripe_account_id": stripe_account_id,
            "amount": payout_amount,
            "currency": get_currency_code(country),
            "method": "instant",
            "external_account_id": self.request.payout_stripe_card_id,
            "statement_descriptor": DEFAULT_STATEMENT_DESCRIPTOR,
            "idempotency_key": "instant-payout-{}".format(payout_idempotency_key),
            "metadata": {"service_origin": "payout"},
        }
        stripe_payout_request_data = StripePayoutRequestCreate(
            payout_id=payout_id,
            idempotency_key="{}-request".format(payout_idempotency_key),
            payout_method_id=payout_method_id,
            stripe_account_id=stripe_account_id,
            request=request,
            status="new",
        )
        stripe_payout_request = await self.create_stripe_payout_request(
            stripe_payout_request_data
        )

        try:
            response = await self.create_stripe_payout(
                country=country,
                payout_amount=payout_amount,
                stripe_account=models.StripeAccountId(stripe_account_id),
            )
            self.logger.info(
                f"[Fast Pay Local Creation] succeed to create a stripe payout. stripe_payout.id: {response.id}",
                payout_account_id=payout_account_id,
                payout_id=payout_id,
            )
            payout_status = response.status
            update_request = StripePayoutRequestUpdate(
                stripe_payout_id=response.id, response=response
            )
            if stripe_payout_request.status != payout_status:
                update_request = StripePayoutRequestUpdate(
                    stripe_payout_id=response.id,
                    response=response,
                    status=payout_status,
                )
                if payout_status in {
                    StripePayoutStatus.FAILED.value,
                    StripePayoutStatus.CANCELED.value,
                    StripePayoutStatus.PAID.value,
                }:
                    update_request = StripePayoutRequestUpdate(
                        stripe_payout_id=response.id,
                        response=response,
                        status=payout_status,
                        received_at=datetime.utcnow(),
                    )
            await self.stripe_payout_request_repo.update_stripe_payout_request_by_id(
                stripe_payout_request_id=stripe_payout_request.id, data=update_request
            )
        except APIConnectionError as error:
            payout_status = StripePayoutStatus.FAILED.value
            await self.update_stripe_payout_request_status(
                stripe_payout_request=stripe_payout_request,
                stripe_payout_status=payout_status,
            )
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe payout due to APIConnectionError.",
                payout_account_id=payout_account_id,
                payout_id=payout_id,
                error=error.json_body,
            )
            error_info = error.json_body.get("error", {})
            error_message = error_info.get("message")
            raise PayoutError(
                http_status_code=error.http_status,
                error_code=PayoutErrorCode.API_CONNECTION_ERROR,
                error_message=error_message,
                retryable=True,
            )
        except RateLimitError as error:
            payout_status = StripePayoutStatus.FAILED.value
            await self.update_stripe_payout_request_status(
                stripe_payout_request=stripe_payout_request,
                stripe_payout_status=payout_status,
            )
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe payout due to RateLimitError.",
                payout_account_id=payout_account_id,
                payout_id=payout_id,
                error=error.json_body,
            )
            error_info = error.json_body.get("error", {})
            error_message = error_info.get("message")
            raise PayoutError(
                http_status_code=error.http_status,
                error_code=PayoutErrorCode.RATE_LIMIT_ERROR,
                error_message=error_message,
                retryable=True,
            )
        except StripeError as error:
            payout_status = StripePayoutStatus.FAILED.value
            await self.update_stripe_payout_request_status(
                stripe_payout_request=stripe_payout_request,
                stripe_payout_status=payout_status,
            )
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe payout due to StripeError.",
                payout_account_id=payout_account_id,
                payout_id=payout_id,
                error=error.json_body,
            )
            error_info = error.json_body.get("error", {})
            error_message = error_info.get("message")
            raise PayoutError(
                http_status_code=error.http_status,
                error_code=PayoutErrorCode.STRIPE_SUBMISSION_ERROR,
                error_message=error_message,
                retryable=False,
            )
        except Exception:
            # Note: we don't know if this transfer succeeded or not, so we assume it didn't and dont
            # persist the request. Re-attempts will reuse the same idempotency key.
            payout_status = StripePayoutStatus.FAILED.value
            await self.update_stripe_payout_request_status(
                stripe_payout_request=stripe_payout_request,
                stripe_payout_status=payout_status,
            )
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe payout due to other error.",
                payout_account_id=payout_account_id,
                payout_id=payout_id,
            )
            raise PayoutError(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=PayoutErrorCode.OTHER_ERROR,
                retryable=True,
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
        self.logger.info(
            f"[Fast Payout Local Creation] succeed to create a sma transfer. sma_transfer.id: {sma_transfer.id}",
            stripe_managed_account_id=stripe_managed_account.id,
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
                    get_currency_code(stripe_managed_account.country_shortname)
                ),
                destination=models.Destination(sma_transfer.to_stripe_account_id),
                country=models.CountryCode(stripe_managed_account.country_shortname),
                request=models.StripeCreateTransferRequest(),
            )
            self.logger.info(
                f"[Fast Pay Local Creation] succeed to create a stripe transfer. stripe_transfer.id: {response.id}",
                stripe_managed_account_id=stripe_managed_account.id,
                stripe_managed_account_transfer_id=sma_transfer.id,
            )
            return response
        except APIConnectionError as error:
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe transfer due to APIConnectionError.",
                stripe_managed_account_id=stripe_managed_account.id,
                stripe_managed_account_transfer_id=sma_transfer.id,
                error=error.json_body,
            )
            error_info = error.json_body.get("error", {})
            error_message = error_info.get("message")
            raise PayoutError(
                http_status_code=error.http_status,
                error_code=PayoutErrorCode.API_CONNECTION_ERROR,
                error_message=error_message,
                retryable=True,
            )
        except StripeError as error:
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe transfer due to StripeError.",
                stripe_managed_account_id=stripe_managed_account.id,
                stripe_managed_account_transfer_id=sma_transfer.id,
                error=error.json_body,
            )
            error_info = error.json_body.get("error", {})
            error_message = error_info.get("message")
            raise PayoutError(
                http_status_code=error.http_status,
                error_code=PayoutErrorCode.STRIPE_SUBMISSION_ERROR,
                error_message=error_message,
                retryable=False,
            )
        except Exception:
            # Note: we don't know if this transfer succeeded or not, so we assume it didn't and dont
            # persist the request. Re-attempts will reuse the same idempotency key.
            self.logger.info(
                "[Fast Payout Local Creation] fail to create a stripe transfer due to other error.",
                stripe_managed_account_id=stripe_managed_account.id,
                stripe_managed_account_transfer_id=sma_transfer.id,
            )
            raise PayoutError(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=PayoutErrorCode.OTHER_ERROR,
                retryable=True,
            )

    async def create_stripe_payout_request(
        self, data: StripePayoutRequestCreate
    ) -> StripePayoutRequest:
        stripe_payout_request = await self.stripe_payout_request_repo.create_stripe_payout_request(
            data
        )
        self.logger.info(
            f"[Fast Payout Local Creation] succeed to create a stripe payout request. stripe_payout_request.id: {stripe_payout_request.id}",
            payout_id=data.payout_id,
            stripe_account_id=data.stripe_account_id,
        )
        return stripe_payout_request

    async def create_stripe_payout(
        self,
        country: models.CountryCode,
        payout_amount: int,
        stripe_account: models.StripeAccountId,
    ) -> models.Payout:
        request = models.StripeCreatePayoutRequest(
            method="instant", metadata={"service_origin": "payment-service"}
        )
        response = await self.stripe_async_client.create_payout(
            country=country,
            currency=models.Currency(get_currency_code(country)),
            amount=models.Amount(payout_amount),
            stripe_account=stripe_account,
            request=request,
        )
        return response

    async def update_stripe_payout_request_status(
        self, stripe_payout_request: StripePayoutRequest, stripe_payout_status: str
    ):
        if stripe_payout_request.status != stripe_payout_status:
            data = StripePayoutRequestUpdate(status=stripe_payout_status)
            if stripe_payout_status in {
                StripePayoutStatus.FAILED.value,
                StripePayoutStatus.CANCELED.value,
                StripePayoutStatus.PAID.value,
            }:
                data = StripePayoutRequestUpdate(
                    status=stripe_payout_status, received_at=datetime.utcnow()
                )
            await self.stripe_payout_request_repo.update_stripe_payout_request_by_id(
                stripe_payout_request_id=stripe_payout_request.id, data=data
            )

from typing import Optional, Union, Tuple

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from stripe.error import StripeError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.types import CountryCode
from app.payout.core.account.utils import get_country_shortname
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.commons.providers.stripe import stripe_models as models
from app.payout.types import PayoutAccountId


class CancelPayoutResponse(OperationResponse):
    pass


class CancelPayoutRequest(OperationRequest):
    transfer_id: models.TransferId
    payout_account_id: PayoutAccountId


class CancelPayout(AsyncOperation[CancelPayoutRequest, CancelPayoutResponse]):
    """
    Processor to cancel a payout.
    """

    stripe_transfer_repo: StripeTransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: CancelPayoutRequest,
        *,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe = stripe

    async def _execute(self) -> CancelPayoutResponse:
        self.logger.info(
            "Cancelling payout.",
            transfer_id=self.request.transfer_id,
            payment_account_id=self.request.payout_account_id,
        )
        transfer_id = int(self.request.transfer_id)
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            payment_account_id=self.request.payout_account_id
        )
        if not payment_account:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID,
                retryable=False,
            )

        stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer_id
        )

        if (
            not stripe_transfer
            or not stripe_transfer.stripe_account_type == "stripe_managed_account"
        ):
            self.logger.info(
                "Failed to get valid stripe managed account.",
                payment_account_id=self.request.payout_account_id,
            )
            return CancelPayoutResponse()
        await self.cancel_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

        self.logger.info(
            "Cancelled payout.",
            transfer_id=self.request.transfer_id,
            payment_account_id=self.request.payout_account_id,
        )
        return CancelPayoutResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, CancelPayoutResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def cancel_stripe_transfer(
        self, stripe_transfer: StripeTransfer, payment_account: PaymentAccount
    ):
        """
        Cancel a transfer. Can only happen if status is pending
        """
        stripe_transfer, transfer_of_stripe = await self.sync_stripe_status(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        if stripe_transfer.stripe_status == "pending":
            if not transfer_of_stripe:
                return
            cancel_request = models.StripeCancelPayoutRequest(
                sid=stripe_transfer.stripe_id,
                stripe_account=stripe_transfer.stripe_account_id,
            )
            country_code = (
                stripe_transfer.country_shortname
                if stripe_transfer.country_shortname
                else get_country_shortname(
                    payment_account=payment_account,
                    payment_account_repository=self.payment_account_repo,
                )
            )
            if not country_code:
                # in dsj, if no country_shortname found, we use "US" as default when retrieving payout
                country_code = CountryCode.US.value

            canceled_payout = await self.stripe.cancel_payout(
                request=cancel_request, country=models.CountryCode(country_code)
            )
            update_request = StripeTransferUpdate(stripe_status=canceled_payout.status)
            await self.stripe_transfer_repo.update_stripe_transfer_by_id(
                stripe_transfer_id=stripe_transfer.id, data=update_request
            )
        else:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_PAYOUT,
                retryable=False,
            )

    async def sync_stripe_status(
        self, stripe_transfer: StripeTransfer, payment_account: PaymentAccount
    ) -> Tuple[StripeTransfer, Optional[models.Payout]]:
        """
        Retrieve latest Stripe Transfer and sync up the status
        :param stripe_transfer: StripeTransfer
        :param payment_account: PaymentAccount
        :return: Tuple, StripeTransfer must exist while stripe payout can be optional
        """
        transfer_of_stripe = await self.get_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        if transfer_of_stripe is None:
            return stripe_transfer, None
        update_request = StripeTransferUpdate(stripe_status=transfer_of_stripe.status)
        updated_stripe_transfer = await self.stripe_transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id, data=update_request
        )

        assert updated_stripe_transfer, "stripe_transfer must exist"
        return updated_stripe_transfer, transfer_of_stripe

    async def get_stripe_transfer(
        self, stripe_transfer: StripeTransfer, payment_account: PaymentAccount
    ) -> Optional[models.Payout]:
        """
        Get Stripe payout by stripe id
        :param stripe_transfer: StripeTransfer
        :param payment_account: PaymentAccount
        :return:  None if stripe transfer doesn't have stripe id; else Stripe payout from Stripe
        """
        if not stripe_transfer.stripe_id:
            return None
        try:
            request = models.StripeRetrievePayoutRequest(
                id=stripe_transfer.stripe_id,
                stripe_account=stripe_transfer.stripe_account_id,
            )
            country_code = (
                stripe_transfer.country_shortname
                if stripe_transfer.country_shortname
                else get_country_shortname(
                    payment_account=payment_account,
                    payment_account_repository=self.payment_account_repo,
                )
            )
            if not country_code:
                # in dsj, if no country_shortname found, we use "US" as default when retrieving payout
                country_code = CountryCode.US.value
            payout = await self.stripe.retrieve_payout(
                country=models.CountryCode(country_code), request=request
            )
            return payout
        except StripeError as e:
            error_info = e.json_body.get("error", {})
            stripe_error_message = error_info.get("message")
            stripe_error_type = error_info.get("type")
            stripe_error_code = error_info.get("code")
            self.logger.exception(
                "Error retrieve stripe payout",
                stripe_id=stripe_transfer.stripe_id,
                stripe_message=stripe_error_message,
                stripe_error_code=stripe_error_code,
                stripe_error_type=stripe_error_type,
            )
            raise PayoutError(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=PayoutErrorCode.OTHER_ERROR,
                error_message="Error retrieve stripe payout",
                retryable=True,
            )

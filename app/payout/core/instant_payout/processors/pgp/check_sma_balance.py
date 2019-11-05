from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.instant_payout.models import CheckSMABalanceRequest, SMABalance


class CheckSMABalance(AsyncOperation[CheckSMABalanceRequest, SMABalance]):
    """Check Stripe Connected Account Balance.

    Call Stripe to Check the available balance of the connected account. If stripe_id does not exist, stripe will raise
    stripe.error.AuthenticationError, which will be translated into PGPAuthenticationError.

    If the stripe response of Balance is mal-formatted, will return 0.
    """

    def __init__(
        self,
        request: CheckSMABalanceRequest,
        stripe_client: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.stripe_managed_account_id = request.stripe_managed_account_id
        self.country = request.country
        self.stripe_client = stripe_client

    async def _execute(self) -> SMABalance:
        balance = await self.stripe_client.retrieve_balance_with_stripe_error_translation(
            stripe_account=self.stripe_managed_account_id, country=self.country
        )
        try:
            amount = balance.available[0].amount
        except (AttributeError, IndexError) as e:
            self.logger.warn(
                "Unable to get SMA balance",
                stripe_managed_account_id=self.stripe_managed_account_id,
                country=self.country,
                error=str(e),
            )
            amount = 0
        return SMABalance(balance=amount)

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, SMABalance]:
        raise

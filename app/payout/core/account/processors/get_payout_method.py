from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
import app.payout.core.account.models as account_models
from app.payout.core.exceptions import (
    payout_method_not_found_error,
    payout_card_not_found_error,
    payout_account_not_match_error,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.models import PayoutAccountId, PayoutMethodId


class GetPayoutMethodRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    payout_method_id: PayoutMethodId


class GetPayoutMethod(
    AsyncOperation[GetPayoutMethodRequest, account_models.PayoutCardInternal]
):
    """
    Processor to get a payout method
    """

    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface

    def __init__(
        self,
        request: GetPayoutMethodRequest,
        *,
        payout_card_repo: PayoutCardRepositoryInterface,
        payout_method_repo: PayoutMethodRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo

    async def _execute(self) -> account_models.PayoutCardInternal:
        payout_method = await self.payout_method_repo.get_payout_method_by_id(
            payout_method_id=self.request.payout_method_id
        )
        if not payout_method:
            self.logger.error(
                "[Payout Account] no payout method existing for the given id",
                payout_method_id=self.request.payout_method_id,
            )
            raise payout_method_not_found_error()

        if payout_method.payment_account_id != self.request.payout_account_id:
            self.logger.error(
                "[Payout Account] payment account for the payout method does not match with the one passed in",
                payout_method_id=self.request.payout_method_id,
            )
            raise payout_account_not_match_error()

        payout_card = await self.payout_card_repo.get_payout_card_by_id(
            payout_method.id
        )
        if not payout_card:
            self.logger.warning(
                "[Payout Account] no payout card existing for payout account while there's matching payout_method",
                payout_account_id=self.request.payout_account_id,
                payout_method_id=payout_method.id,
            )
            raise payout_card_not_found_error()

        return account_models.PayoutCardInternal(
            stripe_card_id=payout_card.stripe_card_id,
            last4=payout_card.last4,
            brand=payout_card.brand,
            exp_month=payout_card.exp_month,
            exp_year=payout_card.exp_year,
            fingerprint=payout_card.fingerprint,
            payout_account_id=payout_method.payment_account_id,
            currency=payout_method.currency,
            country=payout_method.country,
            is_default=payout_method.is_default,
            id=payout_method.id,
            token=payout_method.token,
            created_at=payout_method.created_at,
            updated_at=payout_method.updated_at,
            deleted_at=payout_method.deleted_at,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutCardInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

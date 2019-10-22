from structlog.stdlib import BoundLogger
from typing import Optional, Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account import models as account_models
from app.payout.core.exceptions import (
    payout_method_not_found_for_account_error,
    payout_card_not_found_for_account_error,
    default_payout_card_not_found_error,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.models import PayoutAccountId


class GetDefaultPayoutCardRequest(OperationRequest):
    payout_account_id: PayoutAccountId


class GetDefaultPayoutCard(
    AsyncOperation[GetDefaultPayoutCardRequest, account_models.PayoutCardInternal]
):
    """
    Processor to get a default payout card
    """

    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface

    def __init__(
        self,
        request: GetDefaultPayoutCardRequest,
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
        payout_methods = await self.payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=self.request.payout_account_id
        )
        if not payout_methods:
            self.logger.warning(
                "No payout method existing for payout account.",
                payout_account_id=self.request.payout_account_id,
            )
            raise payout_method_not_found_for_account_error()

        payout_method_ids = [payout_method.id for payout_method in payout_methods]
        payout_cards = await self.payout_card_repo.list_payout_cards_by_ids(
            payout_method_ids
        )
        if not payout_cards:
            self.logger.warning(
                "No payout card existing for payout account.",
                payout_account_id=self.request.payout_account_id,
                matching_payout_method_ids=payout_method_ids,
            )
            raise payout_card_not_found_for_account_error()

        payout_cards_map = {payout_card.id: payout_card for payout_card in payout_cards}
        payout_card_method: Optional[account_models.PayoutCardInternal] = None
        for payout_method in payout_methods:
            payout_card = payout_cards_map.get(payout_method.id)
            if payout_card and payout_method.is_default:
                payout_card_method = account_models.PayoutCardInternal(
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
        if not payout_card_method:
            self.logger.warning(
                "No default payout card for existing payout account.",
                payout_account_id=self.request.payout_account_id,
            )
            raise default_payout_card_not_found_error()
        return payout_card_method

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutCardInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

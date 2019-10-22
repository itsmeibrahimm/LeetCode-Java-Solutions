from structlog.stdlib import BoundLogger
from typing import Union, Optional, List

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account import models as account_models
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.models import PayoutAccountId, PayoutExternalAccountType


class ListPayoutMethodRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    payout_method_type: Optional[
        PayoutExternalAccountType
    ] = PayoutExternalAccountType.CARD
    limit: Optional[int] = 50


class ListPayoutMethod(
    AsyncOperation[ListPayoutMethodRequest, account_models.PayoutCardListInternal]
):
    """
    Processor to get a payout method
    """

    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface

    def __init__(
        self,
        request: ListPayoutMethodRequest,
        *,
        payout_card_repo: PayoutCardRepositoryInterface,
        payout_method_repo: PayoutMethodRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo

    async def _execute(self) -> account_models.PayoutCardListInternal:
        payout_method_list = await self.payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=self.request.payout_account_id,
            payout_method_type=self.request.payout_method_type,
            limit=self.request.limit,
        )
        if len(payout_method_list) == 0:
            return account_models.PayoutCardListInternal(data=[])

        payout_card_ids = [payout_method.id for payout_method in payout_method_list]
        payout_card_list = await self.payout_card_repo.list_payout_cards_by_ids(
            payout_card_ids
        )
        payout_card_map = {
            payout_card.id: payout_card for payout_card in payout_card_list
        }
        payout_card_internal_list: List[account_models.PayoutCardInternal] = []
        for payout_method in payout_method_list:
            card = payout_card_map.get(payout_method.id, None)
            if not card:
                self.logger.warning(
                    "payout_card does not exist for payout_method",
                    payout_method_id=payout_method.id,
                )
            else:
                payout_card_internal = account_models.PayoutCardInternal(
                    stripe_card_id=card.stripe_card_id,
                    last4=card.last4,
                    brand=card.brand,
                    exp_month=card.exp_month,
                    exp_year=card.exp_year,
                    fingerprint=card.fingerprint,
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
                payout_card_internal_list.append(payout_card_internal)
        return account_models.PayoutCardListInternal(data=payout_card_internal_list)

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutCardListInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

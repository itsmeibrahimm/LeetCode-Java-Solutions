from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.payout.core.errors import (
    InstantPayoutBadRequestError,
    InstantPayoutErrorCode,
    instant_payout_error_message_maps,
)
from app.payout.core.instant_payout.models import (
    GetPayoutCardRequest,
    PayoutCardResponse,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface


class GetPayoutCard(AsyncOperation[GetPayoutCardRequest, PayoutCardResponse]):
    """Get Payout Card for Instant Payout.
    """

    def __init__(
        self,
        request: GetPayoutCardRequest,
        payout_method_repo: PayoutMethodRepositoryInterface,
        payout_card_repo: PayoutCardRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.stripe_card_id = request.stripe_card_id
        self.payout_method_repo = payout_method_repo
        self.payout_card_repo = payout_card_repo

    async def _execute(self) -> PayoutCardResponse:
        # Check Payout card existence, it's required to perform a instant payout
        if self.stripe_card_id:
            payout_card = await self.payout_card_repo.get_payout_card_by_stripe_id(
                stripe_card_id=self.stripe_card_id
            )
            if payout_card is None:
                self.logger.warn(
                    "[Instant Payout Submit]: fail to get payout card by stripe id",
                    request=self.request.dict(),
                )
                raise InstantPayoutBadRequestError(
                    InstantPayoutErrorCode.PAYOUT_CARD_NOT_EXIST,
                    error_message=instant_payout_error_message_maps[
                        InstantPayoutErrorCode.PAYOUT_CARD_NOT_EXIST
                    ],
                )
            return PayoutCardResponse(
                payout_card_id=payout_card.id, stripe_card_id=self.stripe_card_id
            )

        # Get default payout card if stripe_card_id is not provided
        payout_methods = await self.payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=self.payout_account_id
        )
        payout_method_ids = [
            payout_method.id
            for payout_method in payout_methods
            if payout_method.is_default
        ]
        payout_cards = await self.payout_card_repo.list_payout_cards_by_ids(
            payout_method_ids
        )
        payout_card = payout_cards[0] if payout_cards else None

        if not payout_card:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to no default payout card",
                request=self.request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.NO_DEFAULT_PAYOUT_CARD,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.NO_DEFAULT_PAYOUT_CARD
                ],
            )

        return PayoutCardResponse(
            payout_card_id=payout_card.id, stripe_card_id=payout_card.stripe_card_id
        )

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, PayoutCardResponse]:
        raise

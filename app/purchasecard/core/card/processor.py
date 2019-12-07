from datetime import datetime
from typing import Optional

from structlog import BoundLogger

from app.commons.core.errors import (
    MarqetaCannotAssignCardError,
    MarqetaCannotMoveCardToNewCardHolderError,
    MarqetaCannotActivateCardError,
    MarqetaCannotInactivateCardError,
    MarqetaNoActiveCardOwnershipError,
    MarqetaCardNotFoundError,
)
from app.purchasecard.core.card.models import (
    InternalAssociateCardResponse,
    InternalUnassociateCardResponse,
    InternalGetMarqetaCardResponse,
)
from app.purchasecard.marqeta_external import errors as marqeta_errors
from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from app.purchasecard.marqeta_external.models import MarqetaProviderGetCardRequest
from app.purchasecard.models.maindb.marqeta_card_transition import TransitionState
from app.purchasecard.repository.marqeta_card import MarqetaCardRepositoryInterface
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepositoryInterface,
)
from app.purchasecard.repository.marqeta_card_transition import (
    MarqetaCardTransitionRepositoryInterface,
)


class CardProcessor:
    logger: BoundLogger
    card_repo: MarqetaCardRepositoryInterface
    card_ownership_repo: MarqetaCardOwnershipRepositoryInterface
    card_transition_repo: MarqetaCardTransitionRepositoryInterface

    def __init__(
        self,
        logger: BoundLogger,
        marqeta_client: MarqetaProviderClient,
        card_repo: MarqetaCardRepositoryInterface,
        card_ownership_repo: MarqetaCardOwnershipRepositoryInterface,
        card_transition_repo: MarqetaCardTransitionRepositoryInterface,
    ):
        self.logger = logger
        self.marqeta_client = marqeta_client
        self.card_repo = card_repo
        self.card_ownership_repo = card_ownership_repo
        self.card_transition_repo = card_transition_repo

    def _get_card_token(self, delight_number):
        if delight_number > self.marqeta_client.get_card_token_prefix_cutover_id():
            return "card-" + str(delight_number)
        else:
            return "delight-" + str(delight_number)

    async def associate_card_with_dasher(
        self,
        delight_number: int,
        last4: str,
        dasher_id: int,
        user_token: str,
        is_dispatcher: Optional[bool] = False,
    ) -> InternalAssociateCardResponse:
        # Look up the card by the delight number and last4
        card_token = self._get_card_token(delight_number)
        get_card_req = MarqetaProviderGetCardRequest(token=card_token, last4=last4)
        card_data = await self.marqeta_client.get_marqeta_card_and_verify(
            req=get_card_req
        )

        num_prev_owners = 0
        card, created = await self.get_or_create_card(
            token=card_data.token, delight_number=delight_number, last4=last4
        )

        # If anyone already owns the card, end their ownership
        if not created:
            previous_ownerships = await self.card_ownership_repo.get_active_card_ownerships_by_card_id(
                card.token
            )
            num_prev_owners = len(previous_ownerships)

            if num_prev_owners == 1 and previous_ownerships[0].dasher_id != dasher_id:
                if is_dispatcher:
                    await self.card_ownership_repo.update_card_ownership_ended_at(
                        marqeta_card_ownership_id=previous_ownerships[0].id,
                        ended_at=datetime.utcnow(),
                    )
                else:
                    raise MarqetaCannotAssignCardError()

        # if dasher already has a different card, relinquish ownership
        old_card_ownership = await self.card_ownership_repo.get_active_card_ownership_by_dasher_id(
            dasher_id=dasher_id
        )
        old_card_relinquished = False
        if old_card_ownership and old_card_ownership.card_id != card_token:
            await self.transition_card(
                card_id=old_card_ownership.card_id,
                desired_state=TransitionState.INACTIVE,
            )
            # update card ownership end time
            await self.card_ownership_repo.update_card_ownership_ended_at(
                marqeta_card_ownership_id=old_card_ownership.id,
                ended_at=datetime.utcnow(),
            )
            old_card_relinquished = True

        try:
            # assign new card to dasher
            await self.marqeta_client.update_card_user_token(
                token=card_token, user_token=user_token
            )
        except marqeta_errors.MarqetaCannotMoveCardToNewCardHolderError:
            raise MarqetaCannotMoveCardToNewCardHolderError()

        await self.card_ownership_repo.create_card_ownership(
            dasher_id=dasher_id, card_id=card_token
        )

        # activate new card
        await self.transition_card(
            card_id=card_token, desired_state=TransitionState.ACTIVE
        )

        return InternalAssociateCardResponse(
            old_card_relinquished=old_card_relinquished, num_prev_owners=num_prev_owners
        )

    async def unassociate_card_from_dasher(
        self, dasher_id: int
    ) -> InternalUnassociateCardResponse:
        card_ownership = await self.card_ownership_repo.get_active_card_ownership_by_dasher_id(
            dasher_id
        )
        if not card_ownership:
            raise MarqetaNoActiveCardOwnershipError()

        await self.transition_card(
            card_id=card_ownership.card_id, desired_state=TransitionState.INACTIVE
        )
        # update card ownership end time
        await self.card_ownership_repo.update_card_ownership_ended_at(
            marqeta_card_ownership_id=card_ownership.id, ended_at=datetime.utcnow()
        )

        return InternalUnassociateCardResponse(token=card_ownership.card_id)

    async def get_marqeta_card_by_dasher_id(
        self, dasher_id
    ) -> InternalGetMarqetaCardResponse:
        card_ownership = await self.card_ownership_repo.get_active_card_ownership_by_dasher_id(
            dasher_id
        )
        if not card_ownership:
            raise MarqetaNoActiveCardOwnershipError()

        card = await self.card_repo.get_by_token(token=card_ownership.card_id)
        if not card:
            raise MarqetaCardNotFoundError()
        return InternalGetMarqetaCardResponse(
            token=card.token,
            delight_number=card.delight_number,
            terminated_at=card.terminated_at,
            last4=card.last4,
        )

    async def get_or_create_card(self, token: str, delight_number: int, last4: str):
        card = await self.card_repo.get(
            token=token, delight_number=delight_number, last4=last4
        )
        if not card:
            card = await self.card_repo.create(
                token=token, delight_number=delight_number, last4=last4
            )
            return card, True
        return card, False

    async def transition_card(self, card_id: str, desired_state: TransitionState):
        # inactivate failed transitions associated with card
        failed_transitions = await self.card_transition_repo.get_failed_transitions(
            card_id
        )
        failed_transition_ids = [transition.id for transition in failed_transitions]
        await self.card_transition_repo.update_transitions_aborted_at(
            transition_ids=failed_transition_ids, aborted_at=datetime.utcnow()
        )

        # create transition
        transition = await self.card_transition_repo.create_transition(
            card_id=card_id, desired_state=TransitionState.INACTIVE, shift_id=None
        )
        card = None
        if desired_state == TransitionState.ACTIVE:
            try:
                card = await self.marqeta_client.update_card_activation(
                    token=card_id, active=True
                )
            except marqeta_errors.MarqetaAPIError:
                self.logger.info("[marqeta] Failed to activate card %s", card_id)
                raise MarqetaCannotActivateCardError()

        elif desired_state == TransitionState.INACTIVE:
            try:
                card = await self.marqeta_client.update_card_activation(
                    token=card_id, active=False
                )
            except marqeta_errors.MarqetaAPIError:
                self.logger.info("[marqeta] Failed to inactivate card %s", card_id)
                raise MarqetaCannotInactivateCardError()

        if card:
            await self.card_transition_repo.update_transitions_succeeded_at(
                transition_ids=[transition.id], succeeded_at=datetime.utcnow()
            )

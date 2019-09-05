from datetime import datetime
from typing import Optional, List

from app.commons import tracing
from app.commons.database.model import DBEntity, DBRequestModel
from app.payin.core.dispute.model import StripeDispute
from app.payin.core.dispute.types import DisputeIdType
from app.payin.models.maindb import stripe_disputes
from app.payin.repository.base import PayinDBRepository


###########################################################
# Stripe Dispute DBEntity and CRUD operations             #
###########################################################
class StripeDisputeDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: Optional[int] = None  # DB incremental id
    stripe_dispute_id: str
    disputed_at: datetime
    amount: int
    fee: int
    net: int
    currency: Optional[str] = None
    charged_at: datetime
    reason: str
    status: str
    evidence_due_by: datetime
    evidence_submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    stripe_card_id: int
    stripe_charge_id: int

    def to_stripe_dispute(self):
        return StripeDispute(
            id=self.id,
            stripe_dispute_id=self.stripe_dispute_id,
            disputed_at=self.disputed_at,
            amount=self.amount,
            fee=self.fee,
            net=self.net,
            currency=self.currency,
            charged_at=self.charged_at,
            reason=self.reason,
            status=self.status,
            evidence_due_by=self.evidence_due_by,
            evidence_submitted_at=self.evidence_submitted_at,
            updated_at=self.updated_at,
            stripe_card_id=self.stripe_card_id,
            stripe_charge_id=self.stripe_charge_id,
        )


class GetStripeDisputeByIdInput(DBRequestModel):
    stripe_dispute_id: str
    dispute_id_type: Optional[str] = None


class GetAllStripeDisputesByPayerIdInput(DBRequestModel):
    stripe_card_ids: List[int]


class GetAllStripeDisputesByPaymentMethodIdInput(DBRequestModel):
    stripe_card_id: int


class UpdateStripeDisputeInput(DBRequestModel):
    id: str
    evidence: Optional[dict]


class DisputeRepositoryInterface:
    """
    Stripe Dispute repository interface class that exposes complicated CRUD operations for business layer
    """

    async def get_dispute_by_dispute_id(
        self, dispute_input: GetStripeDisputeByIdInput
    ) -> Optional[StripeDisputeDbEntity]:
        ...

    async def list_disputes_by_payer_id(
        self, list_dispute_input: GetAllStripeDisputesByPayerIdInput
    ) -> List[StripeDisputeDbEntity]:
        ...

    async def list_disputes_by_payment_method_id(
        self, list_dispute_input: GetAllStripeDisputesByPaymentMethodIdInput
    ) -> List[StripeDisputeDbEntity]:
        ...


@tracing.set_repository_name("dispute", only_trackable=False)
class DisputeRepository(DisputeRepositoryInterface, PayinDBRepository):
    """
    Dispute repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    async def get_dispute_by_dispute_id(
        self, dispute_input: GetStripeDisputeByIdInput
    ) -> Optional[StripeDisputeDbEntity]:
        if (
            dispute_input.dispute_id_type is None
            or dispute_input.dispute_id_type is DisputeIdType.STRIPE_DISPUTE_ID
        ):
            stmt = stripe_disputes.table.select().where(
                stripe_disputes.stripe_dispute_id == dispute_input.stripe_dispute_id
            )
        else:
            stmt = stripe_disputes.table.select().where(
                stripe_disputes.id == dispute_input.stripe_dispute_id
            )
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeDisputeDbEntity.from_row(row) if row else None

    async def list_disputes_by_payer_id(
        self, input: GetAllStripeDisputesByPayerIdInput
    ) -> List[StripeDisputeDbEntity]:
        stmt = stripe_disputes.table.select().where(
            stripe_disputes.stripe_card_id.in_(input.stripe_card_ids)
        )
        rows = await self.main_database.replica().fetch_all(stmt)
        dispute_db_entities = [StripeDisputeDbEntity.from_row(row) for row in rows]
        return dispute_db_entities

    async def list_disputes_by_payment_method_id(
        self, input: GetAllStripeDisputesByPaymentMethodIdInput
    ) -> List[StripeDisputeDbEntity]:
        stmt = stripe_disputes.table.select().where(
            stripe_disputes.stripe_card_id == input.stripe_card_id
        )
        rows = await self.main_database.replica().fetch_all(stmt)
        dispute_db_entities = [StripeDisputeDbEntity.from_row(row) for row in rows]
        return dispute_db_entities

from typing import Optional

from app.purchasecard.core.utils import enriched_error_parse_int
from app.purchasecard.repository.delivery_funding import (
    DeliveryFundingRepositoryInterface,
)
from app.purchasecard.repository.marqeta_decline_exemption import (
    MarqetaDeclineExemptionRepositoryInterface,
)


class ExemptionProcessor:
    def __init__(
        self,
        delivery_funding_repo: DeliveryFundingRepositoryInterface,
        decline_exemption_repo: MarqetaDeclineExemptionRepositoryInterface,
    ):
        self.delivery_funding_repo = delivery_funding_repo
        self.decline_exemption_repo = decline_exemption_repo

    async def create_exemption(
        self,
        creator_id: str,
        delivery_id: str,
        swipe_amount: int,
        mid: Optional[str] = None,
        dasher_id: Optional[str] = None,
        decline_amount: Optional[int] = None,
    ):
        await self.delivery_funding_repo.create(
            creator_id=enriched_error_parse_int(creator_id, "creator id"),
            delivery_id=enriched_error_parse_int(delivery_id, "delivery id"),
            swipe_amount=swipe_amount,
        )
        if dasher_id and mid and decline_amount:
            await self.decline_exemption_repo.create(
                delivery_id=enriched_error_parse_int(delivery_id, "delivery id"),
                creator_id=enriched_error_parse_int(creator_id, "creator id"),
                amount=decline_amount,
                dasher_id=enriched_error_parse_int(creator_id, "dasher id"),
                mid=mid,
            )

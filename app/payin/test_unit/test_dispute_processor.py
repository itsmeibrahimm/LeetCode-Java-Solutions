import pytest

from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.tests.utils import generate_dispute, FunctionMock


class TestDisputeProcessor:
    """
    Test external facing functions exposed by app/payin/core/dispute/processor.py.
    """

    @pytest.mark.asyncio
    async def test_get_dispute_by_pgp_dispute_id(self, dispute_processor):
        dispute = generate_dispute()
        dispute_processor.dispute_client.get_dispute_object = FunctionMock(
            return_value=dispute
        )
        result = await dispute_processor.get(
            dispute_id=dispute.stripe_dispute_id, dispute_id_type=None
        )
        assert result == dispute

    @pytest.mark.asyncio
    async def test_get_dispute_by_stripe_dispute_id(self, dispute_processor):
        dispute = generate_dispute()
        dispute_processor.dispute_client.get_dispute_object = FunctionMock(
            return_value=dispute
        )
        result = await dispute_processor.get(
            dispute_id=dispute.stripe_dispute_id,
            dispute_id_type=DISPUTE_ID_TYPE.STRIPE_DISPUTE_ID,
        )
        assert result == dispute

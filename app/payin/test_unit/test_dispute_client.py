import pytest

from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.tests.utils import FunctionMock, generate_dispute_db_entity


class TestDisputeClient:
    """
    Test internal facing functions exposed by app/payin/core/dispute/processor.py.
    """

    @pytest.mark.asyncio
    async def test_get_dispute_object_by_pgp_id(self, dispute_client):
        dispute_db_entity = generate_dispute_db_entity()
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=dispute_db_entity
        )
        result = await dispute_client.get_dispute_object(
            dispute_id=dispute_db_entity.stripe_dispute_id
        )
        assert dispute_db_entity.to_stripe_dispute() == result

    @pytest.mark.asyncio
    async def test_get_dispute_object_by_stripe_id(self, dispute_client):
        dispute_db_entity = generate_dispute_db_entity()
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=dispute_db_entity
        )
        result = await dispute_client.get_dispute_object(
            dispute_id=dispute_db_entity.id,
            dispute_id_type=DISPUTE_ID_TYPE.STRIPE_DISPUTE_ID,
        )
        assert dispute_db_entity.to_stripe_dispute() == result

    @pytest.mark.asyncio
    async def test_get_dispute_object_by_invalid_dispute_id_type(self, dispute_client):
        dispute_db_entity = generate_dispute_db_entity()
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=dispute_db_entity
        )
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_client.get_dispute_object(
                dispute_id=dispute_db_entity.id, dispute_id_type="INVALID_ID_TYPE"
            )

        assert (
            payment_error.value.error_code == PayinErrorCode.DISPUTE_READ_INVALID_DATA
        )

    @pytest.mark.asyncio
    async def test_dispute_not_found(self, dispute_client):
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=None
        )
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_client.get_dispute_object(
                dispute_id="NO_ID", dispute_id_type=DISPUTE_ID_TYPE.STRIPE_DISPUTE_ID
            )
        assert payment_error.value.error_code == PayinErrorCode.DISPUTE_NOT_FOUND

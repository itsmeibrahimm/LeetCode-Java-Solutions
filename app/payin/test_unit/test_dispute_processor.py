import pytest

from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.core.types import DisputePayerIdType, DisputePaymentMethodIdType
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

    @pytest.mark.asyncio
    async def test_list_disputes_by_payer_id(self, dispute_processor):
        dispute_list = [generate_dispute()]
        dispute_processor.dispute_client.get_disputes_list = FunctionMock(
            return_value=dispute_list
        )
        result = await dispute_processor.list_disputes(
            payer_id="VALID_PAYER_ID",
            payer_id_type=DisputePayerIdType.DD_PAYMENT_PAYER_ID,
            payment_method_id=None,
            payment_method_id_type=None,
        )
        assert result == dispute_list

    @pytest.mark.asyncio
    async def test_list_disputes_by_payment_method_id(self, dispute_processor):
        dispute_list = [generate_dispute()]
        dispute_processor.dispute_client.get_disputes_list = FunctionMock(
            return_value=dispute_list
        )
        result = await dispute_processor.list_disputes(
            payer_id=None,
            payer_id_type=None,
            payment_method_id="VALID_PAYMENT_METHOD_ID",
            payment_method_id_type=DisputePaymentMethodIdType.DD_PAYMENT_METHOD_ID,
        )
        assert result == dispute_list

    @pytest.mark.asyncio
    async def test_list_disputes_by_no_id(self, dispute_processor):
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_processor.list_disputes(
                payer_id=None,
                payer_id_type=None,
                payment_method_id=None,
                payment_method_id_type=None,
            )
        assert (
            payment_error.value.error_code == PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS
        )

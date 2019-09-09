import pytest

from app.payin.core.dispute.model import DisputeList
from app.payin.core.dispute.types import DisputeIdType
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
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
            dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID,
        )
        assert result == dispute

    @pytest.mark.asyncio
    async def test_list_disputes_by_dd_payment_method_id(self, dispute_processor):
        dispute_list = [generate_dispute()]
        dispute_list_object: DisputeList = DisputeList(
            count=len(dispute_list),
            has_more=False,
            total_amount=sum([dispute.amount for dispute in dispute_list]),
            data=dispute_list,
        )
        dispute_processor.dispute_client.get_disputes_list = FunctionMock(
            return_value=dispute_list
        )
        dispute_processor.dispute_client.get_dispute_list_object = FunctionMock(
            return_value=dispute_list_object
        )
        result = await dispute_processor.list_disputes(
            dd_payment_method_id=1,
            stripe_payment_method_id=None,
            dd_stripe_card_id=None,
            dd_payer_id=None,
            stripe_customer_id=None,
            dd_consumer_id=None,
            start_time=None,
            reasons=None,
            distinct=None,
        )
        assert result == dispute_list_object

    @pytest.mark.asyncio
    async def test_list_disputes_by_no_id(self, dispute_processor):
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_processor.list_disputes(
                dd_payment_method_id=None,
                stripe_payment_method_id=None,
                dd_stripe_card_id=None,
                dd_payer_id=None,
                stripe_customer_id=None,
                dd_consumer_id=None,
                start_time=None,
                reasons=None,
                distinct=None,
            )
        assert (
            payment_error.value.error_code == PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS
        )

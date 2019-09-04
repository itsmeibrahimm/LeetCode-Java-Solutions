from typing import List

import pytest

from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.types import DisputePayerIdType, DisputePaymentMethodIdType
from app.payin.repository.dispute_repo import StripeDisputeDbEntity
from app.payin.repository.payer_repo import PayerDbEntity
from app.payin.repository.payment_method_repo import (
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)
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

    @pytest.mark.asyncio
    async def test_list_disputes_by_payer_id(self, dispute_client):
        dispute_list: List[StripeDisputeDbEntity] = [generate_dispute_db_entity()]
        raw_payer_mock = RawPayer()
        raw_payer_mock.payer_entity = PayerDbEntity(
            id="VALID_PAYED_ID",
            payer_type=DisputePayerIdType.DD_PAYMENT_PAYER_ID,
            country="usd",
            legacy_stripe_customer_id="VALID STRIPE CUSTOMER ID",
        )
        dispute_client.payer_client.get_raw_payer = FunctionMock(
            return_value=raw_payer_mock
        )
        dispute_client.payment_method_client.get_dd_stripe_card_ids_by_stripe_customer_id = FunctionMock(
            return_value=[]
        )
        dispute_client.dispute_repo.list_disputes_by_payer_id = FunctionMock(
            return_value=dispute_list
        )
        result = await dispute_client.get_disputes_list(
            payer_id="VALID_PAYER_ID",
            payer_id_type=DisputePayerIdType.DD_PAYMENT_PAYER_ID,
            payment_method_id=None,
            payment_method_id_type=None,
        )
        assert [entity.to_stripe_dispute() for entity in dispute_list] == result

    @pytest.mark.asyncio
    async def test_list_disputes_by_payment_method_id(self, dispute_client):
        dispute_entity_list = [generate_dispute_db_entity()]
        pgp_entity_mock: PgpPaymentMethodDbEntity = PgpPaymentMethodDbEntity(
            id="VALID_PGP_ID",
            pgp_code="STRIPE",
            pgp_resource_id="VALID_STRIPE_PAYMENT_METHOD_ID",
        )
        stripe_entity_mock: StripeCardDbEntity = StripeCardDbEntity(
            id=1,
            stripe_id="VALID_STRIPE_ID",
            fingerprint="VALID_FINGERPRINT",
            last4="VALID_LAST_4",
            dynamic_last4="VALID_DYNAMIC_LAST_4",
            exp_month="10",
            exp_year="2020",
            type="VALID_TYPE",
            active=True,
        )

        raw_payment_method_mock: RawPaymentMethod = RawPaymentMethod(
            pgp_payment_method_entity=pgp_entity_mock,
            stripe_card_entity=stripe_entity_mock,
        )
        dispute_client.payment_method_client.get_raw_payment_method_no_payer_auth = FunctionMock(
            return_value=raw_payment_method_mock
        )
        dispute_client.dispute_repo.list_disputes_by_payment_method_id = FunctionMock(
            return_value=dispute_entity_list
        )
        result = await dispute_client.get_disputes_list(
            payer_id=None,
            payer_id_type=None,
            payment_method_id="VALID_PAYMENT_METHOD_ID",
            payment_method_id_type=DisputePaymentMethodIdType.DD_PAYMENT_METHOD_ID,
        )
        assert [
            dispute_entity.to_stripe_dispute() for dispute_entity in dispute_entity_list
        ] == result

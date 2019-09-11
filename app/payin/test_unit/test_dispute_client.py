from typing import List

import pytest

from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.dispute.types import DisputeIdType
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.types import PayerIdType
from app.payin.repository.dispute_repo import StripeDisputeDbEntity
from app.payin.repository.payer_repo import PayerDbEntity
from app.payin.repository.payment_method_repo import (
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)
from app.payin.tests.utils import (
    FunctionMock,
    generate_dispute_db_entity,
    generate_consumer_charge_entity,
    generate_dispute_charge_metadata,
)


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
        result = await dispute_client.get_raw_dispute(
            dispute_id=dispute_db_entity.stripe_dispute_id,
            dispute_id_type=DisputeIdType.STRIPE_DISPUTE_ID,
        )
        assert dispute_db_entity.to_stripe_dispute() == result

    @pytest.mark.asyncio
    async def test_get_dispute_object_by_stripe_id(self, dispute_client):
        dispute_db_entity = generate_dispute_db_entity()
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=dispute_db_entity
        )
        result = await dispute_client.get_raw_dispute(
            dispute_id=dispute_db_entity.id,
            dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID,
        )
        assert dispute_db_entity.to_stripe_dispute() == result

    @pytest.mark.asyncio
    async def test_dispute_not_found(self, dispute_client):
        dispute_client.dispute_repo.get_dispute_by_dispute_id = FunctionMock(
            return_value=None
        )
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_client.get_raw_dispute(
                dispute_id="NO_ID", dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID
            )
        assert payment_error.value.error_code == PayinErrorCode.DISPUTE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_disputes_by_dd_payer_id(self, dispute_client):
        dispute_list: List[StripeDisputeDbEntity] = [generate_dispute_db_entity()]
        raw_payer_mock = RawPayer()
        id = generate_object_uuid()
        raw_payer_mock.payer_entity = PayerDbEntity(
            id=id,
            payer_type=PayerIdType.PAYER_ID,
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
        result = await dispute_client.get_raw_disputes_list(
            dd_payment_method_id=None,
            stripe_payment_method_id=None,
            dd_stripe_card_id=None,
            dd_payer_id="VALID_PAYER_ID",
            stripe_customer_id=None,
            dd_consumer_id=None,
            start_time=None,
            reasons=None,
        )
        assert [entity.to_stripe_dispute() for entity in dispute_list] == result

    @pytest.mark.asyncio
    async def test_list_disputes_by_payment_method_id(self, dispute_client):
        dispute_entity_list = [generate_dispute_db_entity()]
        pgp_payment_method_id = generate_object_uuid()
        pgp_entity_mock: PgpPaymentMethodDbEntity = PgpPaymentMethodDbEntity(
            id=pgp_payment_method_id,
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
        dispute_client.payment_method_client.get_raw_payment_method_without_payer_auth = FunctionMock(
            return_value=raw_payment_method_mock
        )
        dispute_client.dispute_repo.list_disputes_by_payment_method_id = FunctionMock(
            return_value=dispute_entity_list
        )
        result = await dispute_client.get_raw_disputes_list(
            dd_payment_method_id="VALID PAYMENT METHOD ID",
            stripe_payment_method_id=None,
            dd_stripe_card_id=None,
            dd_payer_id=None,
            stripe_customer_id=None,
            dd_consumer_id=None,
            start_time=None,
            reasons=None,
        )
        assert [
            dispute_entity.to_stripe_dispute() for dispute_entity in dispute_entity_list
        ] == result

    @pytest.mark.asyncio
    async def test_get_dispute_charge_metadata_object(self, dispute_client):
        charge_metadata_object = generate_dispute_charge_metadata()
        dispute_client.dispute_repo.get_dispute_charge_metadata_attributes = FunctionMock(
            return_value=(
                generate_dispute_db_entity(),
                generate_consumer_charge_entity(),
            )
        )
        dispute_client.payment_method_client.get_stripe_card_id_by_id = FunctionMock(
            return_value="VALID_CARD_ID"
        )
        result = await dispute_client.get_dispute_charge_metadata_object(
            dispute_id=1, dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID
        )
        assert result == charge_metadata_object

    @pytest.mark.asyncio
    async def test_get_dispute_charge_metadata_object_no_dispute_found(
        self, dispute_client
    ):
        dispute_client.dispute_repo.get_dispute_charge_metadata_attributes = FunctionMock(
            return_value=(None, generate_consumer_charge_entity())
        )
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_client.get_dispute_charge_metadata_object(
                dispute_id=1, dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID
            )
        assert payment_error.value.error_code == PayinErrorCode.DISPUTE_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_dispute_charge_metadata_object_consumer_charge_found(
        self, dispute_client
    ):
        dispute_client.dispute_repo.get_dispute_charge_metadata_attributes = FunctionMock(
            return_value=(generate_dispute_db_entity(), None)
        )
        with pytest.raises(DisputeReadError) as payment_error:
            await dispute_client.get_dispute_charge_metadata_object(
                dispute_id=1, dispute_id_type=DisputeIdType.DD_STRIPE_DISPUTE_ID
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE
        )

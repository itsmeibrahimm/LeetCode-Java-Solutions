import uuid
from typing import List

import pytest

from app.commons.core.errors import DBOperationError
from app.commons.types import CountryCode
from app.payin.core.exceptions import PaymentMethodUpdateError, PayinErrorCode
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.repository.payment_method_repo import StripeCardDbEntity
from app.payin.tests.utils import (
    generate_pgp_payment_method,
    FunctionMock,
    generate_stripe_card,
)


class TestPaymentMethodClient:
    """
    Test internal facing functions exposed by app/payin/core/payment_method/payment_method_client.py.
    """

    @pytest.mark.asyncio
    async def test_get_payment_method_list_by_dd_consumer_id(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                stripe_id=pgp_payment_method_list[0].pgp_resource_id, is_scanned=True
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_consumer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_dd_consumer_id(
            dd_consumer_id="1",
            country=CountryCode.US,
            active_only=False,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )

        assert len(payment_method_list) == 1
        assert payment_method_list[0].dd_stripe_card_id == stripe_card_db_entities[0].id
        assert payment_method_list[0].card.is_scanned
        assert payment_method_list[0].card.checks.address_line1_check is None
        assert payment_method_list[0].card.checks.address_postal_code_check is None

    @pytest.mark.asyncio
    async def test_get_active_only_payment_method_list_by_dd_consumer_id(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                active=False, stripe_id=pgp_payment_method_list[0].pgp_resource_id
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_consumer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_dd_consumer_id(
            dd_consumer_id="1",
            country=CountryCode.US,
            active_only=True,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )

        assert len(payment_method_list) == 0

    @pytest.mark.asyncio
    async def test_get_payment_method_list_by_dd_consumer_id_for_country(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                country=CountryCode.AU,
                stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_consumer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_dd_consumer_id(
            dd_consumer_id="1",
            country=CountryCode.US,
            active_only=True,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )

        assert len(payment_method_list) == 0

    @pytest.mark.asyncio
    async def test_get_payment_method_list_by_stripe_customer_id(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                stripe_id=pgp_payment_method_list[0].pgp_resource_id,
                is_scanned=False,
                address_zip_check="passed_postal_check",
                address_line1_check="passed_line1_check",
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_stripe_customer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_stripe_customer_id(
            stripe_customer_id="VALID_STRIPE_CUSTOMER_ID",
            country=CountryCode.US,
            active_only=False,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )
        assert len(payment_method_list) == 1
        payment_method = payment_method_list[0]
        assert payment_method.dd_stripe_card_id == stripe_card_db_entities[0].id
        assert payment_method.card.is_scanned is False
        assert (
            payment_method.card.checks.address_postal_code_check
            == "passed_postal_check"
        )
        assert payment_method.card.checks.address_line1_check == "passed_line1_check"

    @pytest.mark.asyncio
    async def test_get_active_only_payment_method_list_by_stripe_customer_id(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                active=False, stripe_id=pgp_payment_method_list[0].pgp_resource_id
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_stripe_customer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_stripe_customer_id(
            stripe_customer_id="VALID_STRIPE_CUSTOMER_ID",
            country=CountryCode.US,
            active_only=True,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )
        assert len(payment_method_list) == 0

    @pytest.mark.asyncio
    async def test_get_payment_method_list_by_stripe_customer_id_for_country(
        self, payment_method_client
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card_db_entities = [
            generate_stripe_card(
                country=CountryCode.AU,
                stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            )
        ]
        payment_method_client.payment_method_repo.list_stripe_card_db_entities_by_stripe_customer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )
        payment_method_client.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids = FunctionMock(
            return_value=pgp_payment_method_list
        )
        payment_method_list: List[
            PaymentMethod
        ] = await payment_method_client.get_payment_method_list_by_stripe_customer_id(
            stripe_customer_id="VALID_STRIPE_CUSTOMER_ID",
            country=CountryCode.US,
            active_only=False,
            force_update=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
        )
        assert len(payment_method_list) == 0

    @pytest.mark.asyncio
    async def test_get_stripe_cards_for_consumer_id(self, payment_method_client):
        stripe_card_db_entities = [
            StripeCardDbEntity(
                id=uuid.uuid4(),
                stripe_id="",
                fingerprint="",
                last4="",
                dynamic_last4="",
                exp_month="01",
                exp_year="2020",
                type="Visa",
                active=True,
                country_of_origin="US",
                consumer_id=1,
            )
        ]
        payment_method_client.payment_method_repo.get_stripe_cards_by_consumer_id = FunctionMock(
            return_value=stripe_card_db_entities
        )

        stripe_cards: List[
            StripeCardDbEntity
        ] = await payment_method_client.get_stripe_cards_for_consumer_id(
            consumer_id=stripe_card_db_entities[0].consumer_id
        )
        assert len(stripe_cards) == 1
        assert stripe_cards[0].id == stripe_card_db_entities[0].id

    @pytest.mark.asyncio
    async def test_update_stripe_cards_remove_pii(self, payment_method_client):
        stripe_card_db_entities = [
            StripeCardDbEntity(
                id=uuid.uuid4(),
                stripe_id="",
                fingerprint="",
                last4="XXXX",
                dynamic_last4="XXXX",
                exp_month="01",
                exp_year="2020",
                type="Visa",
                active=True,
                country_of_origin="US",
                consumer_id=1,
            )
        ]
        payment_method_client.payment_method_repo.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_card_db_entities
        )

        stripe_cards: List[
            StripeCardDbEntity
        ] = await payment_method_client.update_stripe_cards_remove_pii(
            consumer_id=stripe_card_db_entities[0].consumer_id
        )
        assert len(stripe_cards) == 1
        assert stripe_cards[0].last4 == DeletePayerRedactingText.XXXX
        assert stripe_cards[0].dynamic_last4 == DeletePayerRedactingText.XXXX

    @pytest.mark.asyncio
    async def test_update_stripe_cards_remove_pii_errors(self, payment_method_client):
        stripe_card_db_entities = [
            StripeCardDbEntity(
                id=uuid.uuid4(),
                stripe_id="",
                fingerprint="",
                last4="XXXX",
                dynamic_last4="XXXX",
                exp_month="01",
                exp_year="2020",
                type="Visa",
                active=True,
                country_of_origin="US",
                consumer_id=1,
            )
        ]
        payment_method_client.payment_method_repo.update_stripe_cards_remove_pii = FunctionMock(
            side_effect=DBOperationError(error_message="")
        )

        with pytest.raises(PaymentMethodUpdateError) as e:
            await payment_method_client.update_stripe_cards_remove_pii(
                consumer_id=stripe_card_db_entities[0].consumer_id
            )
        assert e.value.error_code == PayinErrorCode.PAYMENT_METHOD_UPDATE_DB_ERROR

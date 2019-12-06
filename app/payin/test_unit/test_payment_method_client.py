from typing import List

import pytest

from app.commons.types import CountryCode
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.types import PaymentMethodSortKey
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
            generate_stripe_card(stripe_id=pgp_payment_method_list[0].pgp_resource_id)
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
            generate_stripe_card(stripe_id=pgp_payment_method_list[0].pgp_resource_id)
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
        assert payment_method_list[0].dd_stripe_card_id == stripe_card_db_entities[0].id

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

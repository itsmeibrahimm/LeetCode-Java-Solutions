from datetime import datetime
from uuid import uuid4

import pytest
from pytz import timezone

from app.commons.types import CountryCode
from app.payin.core.payer.types import PayerType
from app.payin.repository.payer_repo import (
    PayerRepository,
    InsertPayerInput,
    GetPayerByIdInput,
    InsertPgpCustomerInput,
    GetPgpCustomerInput,
    UpdatePgpCustomerSetInput,
    UpdatePgpCustomerWhereInput,
)


class TestPayerRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_payer_timestamp_timezone(self, payer_repository: PayerRepository):
        created_at = datetime.now(timezone("Europe/Amsterdam"))
        insert_payer_input = InsertPayerInput(
            id=uuid4(),
            payer_type=PayerType.STORE,
            country=CountryCode.US,
            created_at=created_at,
        )
        payer = await payer_repository.insert_payer(insert_payer_input)
        get_payer = await payer_repository.get_payer_by_id(
            GetPayerByIdInput(id=payer.id)
        )

        assert payer is not None
        assert get_payer is not None
        assert payer == get_payer
        assert get_payer.created_at is not None
        assert created_at.timestamp() == get_payer.created_at.timestamp()

    async def test_pgp_customer_crud(self, payer_repository: PayerRepository):
        # TODO: [PAYIN-37] don't need to create payer after we remove the foreign key constraint
        insert_payer_input = InsertPayerInput(
            id=uuid4(), payer_type=PayerType.STORE, country=CountryCode.US
        )
        payer = await payer_repository.insert_payer(insert_payer_input)

        # test insert and get
        insert_pgp_customer_input = InsertPgpCustomerInput(
            id=uuid4(),
            payer_id=payer.id,
            pgp_resource_id="fake_stripe_customer_id",
            country="US",
            is_primary=True,
            pgp_code="stripe",
            legacy_id=1,
            account_balance=100,
            default_payment_method_id="fake_default_payment_method_id",
            created_at=datetime.utcnow(),
        )
        pgp_customer = await payer_repository.insert_pgp_customer(
            insert_pgp_customer_input
        )
        assert pgp_customer.country is not None
        assert pgp_customer.is_primary is not None
        assert pgp_customer.legacy_id is not None
        assert pgp_customer.account_balance is not None
        assert pgp_customer.default_payment_method_id is not None

        get_pgp_customer = await payer_repository.get_pgp_customer(
            GetPgpCustomerInput(payer_id=payer.id)
        )
        assert pgp_customer == get_pgp_customer

        # test update and get
        updated_at = datetime.utcnow()
        updated_default_payment_method_id = "new_fake_default_payment_method_id"
        updated_pgp_customer = await payer_repository.update_pgp_customer(
            request_set=UpdatePgpCustomerSetInput(
                updated_at=updated_at,
                default_payment_method_id=updated_default_payment_method_id,
            ),
            request_where=UpdatePgpCustomerWhereInput(id=pgp_customer.id),
        )
        assert (
            updated_pgp_customer.default_payment_method_id
            == updated_default_payment_method_id
        )

        get_pgp_customer = await payer_repository.get_pgp_customer(
            GetPgpCustomerInput(payer_id=payer.id)
        )
        assert updated_pgp_customer == get_pgp_customer

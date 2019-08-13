import asyncio

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository


class TestPaymentAccountRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_create_update_get_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        data = PaymentAccountCreate(
            account_type="some_type",
            account_id=123,
            statement_descriptor="my account",
            entity="dasher",
        )

        created_account = await payment_account_repo.create_payment_account(data)
        assert created_account.id, "account is created, assigned an ID"

        assert created_account == await payment_account_repo.get_payment_account_by_id(
            created_account.id
        ), "retrieved account matches"

        update_data = PaymentAccountUpdate(
            account_type="some_other_type", statement_descriptor="new descriptor"
        )

        updated_account = await payment_account_repo.update_payment_account_by_id(
            payment_account_id=created_account.id, data=update_data
        )

        assert updated_account
        assert updated_account.account_type == update_data.account_type
        assert updated_account.statement_descriptor == update_data.statement_descriptor

    async def test_get_all_payment_accounts_by_account_id_account_type(
        self, payment_account_repo: PaymentAccountRepository
    ):
        account_1 = PaymentAccountCreate(
            account_type="type",
            account_id=1,
            statement_descriptor="i am description yay",
            entity="dasher",
        )
        account_2 = account_1.copy(deep=True, update={"entity": "some other entity!"})

        account_1_created = await payment_account_repo.create_payment_account(account_1)
        account_2_created = await payment_account_repo.create_payment_account(account_2)

        assert account_1.account_type and account_1.account_id

        including_account_1_and_2, nothing, = await asyncio.gather(
            payment_account_repo.get_all_payment_accounts_by_account_id_account_type(
                account_id=account_1.account_id, account_type=account_1.account_type
            ),
            payment_account_repo.get_all_payment_accounts_by_account_id_account_type(
                account_id=-1, account_type=account_1.account_type
            ),
        )

        # Not verifying size of result set ... since we don't rollback test DB writes for now.
        assert (
            account_1_created in including_account_1_and_2
            and account_2_created in including_account_1_and_2  # noqa W503
        )
        assert len(nothing) == 0

    async def test_create_update_get_stripe_managed_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        data = StripeManagedAccountCreate(stripe_id="stripe_id", country_shortname="us")

        created_account = await payment_account_repo.create_stripe_managed_account(data)
        assert created_account.id, "account is created, assigned an ID"

        retrieved_account = await payment_account_repo.get_stripe_managed_account_by_id(
            created_account.id
        )
        assert created_account == retrieved_account, "retrieved account matches"

        update_data = StripeManagedAccountUpdate(
            stripe_id="stripe_id_updated", country_shortname="ca"
        )

        updated_account = await payment_account_repo.update_stripe_managed_account_by_id(
            stripe_managed_account_id=created_account.id, data=update_data
        )

        assert updated_account
        assert updated_account.stripe_id == update_data.stripe_id
        assert updated_account.country_shortname == update_data.country_shortname

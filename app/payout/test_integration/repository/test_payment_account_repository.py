import asyncio
from datetime import datetime, timezone
from typing import cast

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
from app.testcase_utils import validate_expected_items_in_dict


class TestPaymentAccountRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_create_update_get_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        data = PaymentAccountCreate(
            account_id=123,
            account_type="sma",
            entity="dasher",
            resolve_outstanding_balance_frequency="daily",
            payout_disabled=True,
            charges_enabled=True,
            old_account_id=1234,
            upgraded_to_managed_account_at=datetime.now(timezone.utc),
            is_verified_with_stripe=True,
            transfers_enabled=True,
            statement_descriptor="test_statement_descriptor",
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        created_account = await payment_account_repo.create_payment_account(data)
        assert created_account.id, "id shouldn't be None"
        assert created_account.created_at, "created_at shouldn't be None"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created_account.dict()
        )

        assert created_account == await payment_account_repo.get_payment_account_by_id(
            created_account.id
        ), "retrieved account doesn't match created account"

        update_data = PaymentAccountUpdate(
            account_type="some_other_type", statement_descriptor="new descriptor"
        )

        updated_account = await payment_account_repo.update_payment_account_by_id(
            payment_account_id=created_account.id, data=update_data
        )

        assert updated_account
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated_account.dict()
        )

    async def test_get_all_payment_accounts_by_account_id_account_type(
        self, payment_account_repo: PaymentAccountRepository
    ):
        account_1 = PaymentAccountCreate(
            account_type="type",
            account_id=int(datetime.utcnow().timestamp()),
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

        cast(list, including_account_1_and_2)

        # Not verifying size of result set ... since we don't rollback test DB writes for now.
        assert (
            account_1_created in including_account_1_and_2
            and account_2_created in including_account_1_and_2  # noqa W503
        )
        assert (
            including_account_1_and_2.index(account_1_created) == 1
        ), "first created should be returned last"
        assert (
            including_account_1_and_2.index(account_2_created) == 0
        ), "most recently created should be returned first"
        assert len(nothing) == 0

    async def test_create_update_get_stripe_managed_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        data = StripeManagedAccountCreate(
            stripe_id="stripe_id",
            country_shortname="us",
            stripe_last_updated_at=datetime.now(timezone.utc),
            bank_account_last_updated_at=datetime.now(timezone.utc),
            fingerprint="fingerprint",
            default_bank_last_four="last4",
            default_bank_name="bank",
            verification_disabled_reason="no-reason",
            verification_due_by=datetime.now(timezone.utc),
            verification_fields_needed="a lot",
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        created_account = await payment_account_repo.create_stripe_managed_account(data)
        assert created_account.id, "account is created, assigned an ID"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created_account.dict()
        )

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
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated_account.dict()
        )

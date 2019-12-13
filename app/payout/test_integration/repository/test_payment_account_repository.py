import asyncio
from datetime import datetime, timezone
from typing import cast

import pytest

import uuid
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountUpdate,
    StripeManagedAccountCreate,
    StripeManagedAccountCreateAndPaymentAccountUpdate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_managed_account,
)
from app.payout.models import AccountType
from app.testcase_utils import validate_expected_items_in_dict


class TestPaymentAccountRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_create_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

    async def test_create_update_get_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        assert payment_account == await payment_account_repo.get_payment_account_by_id(
            payment_account.id
        ), "retrieved account doesn't match created account"

    async def test_update_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        update_data = PaymentAccountUpdate(statement_descriptor="new descriptor")
        updated_account = await payment_account_repo.update_payment_account_by_id(
            payment_account_id=payment_account.id, data=update_data
        )

        assert updated_account
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated_account.dict()
        )

    async def test_get_all_payment_accounts_by_account_id_account_type(
        self, payment_account_repo: PaymentAccountRepository
    ):
        account_1 = PaymentAccountCreate(
            account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            account_id=int(datetime.utcnow().timestamp()),
            statement_descriptor="i am description yay",
            entity="dasher",
        )
        account_2 = account_1.copy(deep=True, update={"entity": "merchant"})

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
            including_account_1_and_2.index(account_1_created) == 0
        ), "first created should be returned first"
        assert (
            including_account_1_and_2.index(account_2_created) == 1
        ), "most recently created should be returned last"
        assert len(nothing) == 0

    async def test_create_stripe_managed_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )

    async def test_create_update_get_stripe_managed_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        retrieved_account = await payment_account_repo.get_stripe_managed_account_by_id(
            sma.id
        )
        assert sma == retrieved_account, "retrieved account matches"
        update_data = StripeManagedAccountUpdate(
            stripe_id="stripe_id_updated", country_shortname="ca"
        )
        updated_account = await payment_account_repo.update_stripe_managed_account_by_id(
            stripe_managed_account_id=sma.id, data=update_data
        )
        assert updated_account
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated_account.dict()
        )

    async def test_get_last_stripe_managed_account_and_count_by_stripe_id(
        self, payment_account_repo: PaymentAccountRepository
    ):
        stripe_id = str(uuid.uuid4())

        retrieved_sma, count = await payment_account_repo.get_last_stripe_managed_account_and_count_by_stripe_id(
            stripe_id=stripe_id
        )
        assert retrieved_sma is None
        assert count == 0

        # prepare data
        data_1 = StripeManagedAccountCreate(
            stripe_id=stripe_id,
            country_shortname="us",
            stripe_last_updated_at=datetime.now(timezone.utc),
            bank_account_last_updated_at=datetime.now(timezone.utc),
            fingerprint="fingerprint",
            default_bank_last_four="last4",
            default_bank_name="bank",
            verification_disabled_reason="no-reason",
            verification_due_by=datetime.now(timezone.utc),
            verification_fields_needed="a lot",
            verification_status="PENDING",
            verification_error_info="",
        )

        sma_1 = await payment_account_repo.create_stripe_managed_account(data_1)
        retrieved_sma, count = await payment_account_repo.get_last_stripe_managed_account_and_count_by_stripe_id(
            stripe_id=stripe_id
        )
        assert retrieved_sma == sma_1
        assert count == 1

        data_2 = StripeManagedAccountCreate(
            stripe_id=stripe_id,
            country_shortname="CA",
            stripe_last_updated_at=datetime.now(timezone.utc),
            bank_account_last_updated_at=datetime.now(timezone.utc),
            fingerprint="fingerprint",
            default_bank_last_four="last4",
            default_bank_name="bank",
            verification_disabled_reason="no-reason",
            verification_due_by=datetime.now(timezone.utc),
            verification_fields_needed="a lot",
            verification_status="PENDING",
            verification_error_info="",
        )

        sma_2 = await payment_account_repo.create_stripe_managed_account(data_2)
        retrieved_sma, count = await payment_account_repo.get_last_stripe_managed_account_and_count_by_stripe_id(
            stripe_id=stripe_id
        )

        assert retrieved_sma is not None
        assert retrieved_sma.country_shortname == data_2.country_shortname
        assert retrieved_sma == sma_2
        assert count == 2

    async def test_create_stripe_managed_account_and_update_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        country_shortname = "US"
        stripe_id = str(uuid.uuid4())
        data = StripeManagedAccountCreateAndPaymentAccountUpdate(
            country_shortname=country_shortname,
            stripe_id=stripe_id,
            payment_account_id=payment_account.id,
        )
        stripe_managed_account, updated_payment_account = await payment_account_repo.create_stripe_managed_account_and_update_payment_account(
            data=data
        )
        assert stripe_managed_account
        assert stripe_managed_account.stripe_id == stripe_id
        assert stripe_managed_account.country_shortname == country_shortname
        assert updated_payment_account
        assert updated_payment_account.id == payment_account.id
        assert updated_payment_account.account_id == stripe_managed_account.id

    async def test_create_stripe_managed_account_and_update_payment_account_failed(
        self, payment_account_repo: PaymentAccountRepository
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        country_shortname = "US"
        stripe_id = str(uuid.uuid4())
        data = StripeManagedAccountCreateAndPaymentAccountUpdate(
            country_shortname=country_shortname,
            stripe_id=stripe_id,
            payment_account_id=payment_account.id + 1,
        )
        with pytest.raises(AssertionError):
            await payment_account_repo.create_stripe_managed_account_and_update_payment_account(
                data=data
            )
        retrieved_sma, count = await payment_account_repo.get_last_stripe_managed_account_and_count_by_stripe_id(
            stripe_id=stripe_id
        )
        assert retrieved_sma is None
        assert count == 0

    async def test_get_recently_updated_stripe_managed_account_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        first_recently_updated_sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert stripe_managed_account
        second_recently_updated_sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        third_sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo,
            bank_account_last_updated_at=datetime(2019, 6, 1, tzinfo=timezone.utc),
        )
        retrieved_sma_id_list = await payment_account_repo.get_recently_updated_stripe_managed_account_ids(
            last_bank_account_update_allowed_at=datetime(
                2019, 7, 1, tzinfo=timezone.utc
            )
        )
        assert retrieved_sma_id_list
        assert first_recently_updated_sma.id in retrieved_sma_id_list
        assert second_recently_updated_sma.id in retrieved_sma_id_list
        assert third_sma.id not in retrieved_sma_id_list

    async def test_get_recently_updated_stripe_managed_account_not_found(
        self, payment_account_repo: PaymentAccountRepository
    ):
        retrieved_sma_id_list = await payment_account_repo.get_recently_updated_stripe_managed_account_ids(
            last_bank_account_update_allowed_at=datetime.now(timezone.utc)
        )
        assert not retrieved_sma_id_list

    async def test_get_payment_account_ids_by_sma_ids(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert first pair stripe_managed_account and payment account
        first_sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        first_payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=first_sma.id
        )
        # prepare and insert first pair stripe_managed_account and payment account
        second_sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        second_payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=second_sma.id
        )
        sma_ids = [first_sma.id, second_sma.id]
        retrieved_payment_account_ids = await payment_account_repo.get_payment_account_ids_by_sma_ids(
            stripe_managed_account_ids=sma_ids
        )
        assert retrieved_payment_account_ids
        assert first_payment_account.id in retrieved_payment_account_ids
        assert second_payment_account.id in retrieved_payment_account_ids

    async def test_get_payment_account_ids_by_sma_ids_not_found(
        self, payment_account_repo: PaymentAccountRepository
    ):
        assert not await payment_account_repo.get_payment_account_ids_by_sma_ids(
            stripe_managed_account_ids=[]
        )

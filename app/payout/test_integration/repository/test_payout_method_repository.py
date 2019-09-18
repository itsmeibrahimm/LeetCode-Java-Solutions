from datetime import datetime

import pytest

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payout_method import PayoutMethodUpdate
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payout_method,
    prepare_and_insert_payment_account,
    prepare_payout_method_list,
)


class TestPayoutMethodRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_method_repo(self, payout_bankdb: DB) -> PayoutMethodRepository:
        return PayoutMethodRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def payout_card_repo(self, payout_bankdb: DB) -> PayoutCardRepository:
        return PayoutCardRepository(database=payout_bankdb)

    async def test_create_payout_method(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        # prepare and insert payout_method, then validate
        await prepare_and_insert_payout_method(
            payment_account_repo=payment_account_repo,
            payout_method_repo=payout_method_repo,
        )

    async def test_create_get_payout_method(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        # prepare and insert payout_method, then validate
        payout_method = await prepare_and_insert_payout_method(
            payment_account_repo=payment_account_repo,
            payout_method_repo=payout_method_repo,
        )

        assert payout_method == await payout_method_repo.get_payout_method_by_id(
            payout_method.id
        ), "retrieved payout method matches"

    async def test_update_payout_method_deleted_at(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        # prepare and insert payout_method, then validate
        payout_method = await prepare_and_insert_payout_method(
            payment_account_repo=payment_account_repo,
            payout_method_repo=payout_method_repo,
        )
        deleted_at = datetime.utcnow()
        updated_payout_method = await payout_method_repo.update_payout_method_deleted_at(
            token=payout_method.token, data=PayoutMethodUpdate(deleted_at=deleted_at)
        )
        if updated_payout_method:
            assert (
                updated_payout_method.deleted_at == deleted_at
            ), "retrieved payout list matches"

    async def test_list_payout_method_by_payment_account_id(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_method, then validate
        payout_method_list = await prepare_payout_method_list(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        retrieved_payout_account_list = await payout_method_repo.list_payout_cards_by_payout_account_id(
            payout_account_id=payment_account.id
        )
        assert (
            payout_method_list == retrieved_payout_account_list
        ), "retrieved payout method list matches"

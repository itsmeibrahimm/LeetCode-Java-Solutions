import pytest

from app.commons.database.infra import DB
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_payout_card_list,
    prepare_and_insert_payout_card,
    prepare_and_insert_payment_account,
)


class TestPayoutCardRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_card_repo(self, payout_bankdb: DB) -> PayoutCardRepository:
        return PayoutCardRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_method_repo(self, payout_bankdb: DB) -> PayoutMethodRepository:
        return PayoutMethodRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_create_payout_card(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_card, then validate
        await prepare_and_insert_payout_card(
            payout_method_repo=payout_method_repo,
            payout_card_repo=payout_card_repo,
            payout_account_id=payment_account.id,
        )

    async def test_create_get_payout_card(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_card, then validate
        payout_card = await prepare_and_insert_payout_card(
            payout_method_repo=payout_method_repo,
            payout_card_repo=payout_card_repo,
            payout_account_id=payment_account.id,
        )

        assert payout_card == await payout_card_repo.get_payout_card_by_id(
            payout_card.id
        ), "retrieved payout card matches"

    async def test_list_payout_card_by_ids(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_card list, then validate
        payout_card_list = await prepare_payout_card_list(
            payout_method_repo=payout_method_repo,
            payout_card_repo=payout_card_repo,
            payout_account_id=payment_account.id,
        )
        id_list = [payout_card.id for payout_card in payout_card_list]
        assert payout_card_list == await payout_card_repo.list_payout_cards_by_ids(
            id_list
        ), "retrieved payout card list matches"

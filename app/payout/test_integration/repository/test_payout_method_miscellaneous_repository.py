import pytest
from pydantic import ValidationError

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethodMiscellaneousCreate,
)
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.bankdb.payout_method_miscellaneous import (
    PayoutMethodMiscellaneousRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    mock_stripe_card,
    prepare_payout_method_list,
)
from app.payout.types import PayoutExternalAccountType


class TestPayoutMethodMiscellaneousRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def payout_method_repo(self, payout_bankdb: DB) -> PayoutMethodRepository:
        return PayoutMethodRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_method_miscellaneous_repo(
        self, payout_bankdb: DB
    ) -> PayoutMethodMiscellaneousRepository:
        return PayoutMethodMiscellaneousRepository(database=payout_bankdb)

    async def test_unset_default_and_create_payout_method_and_payout_card_success(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert a list of payout_method with 1 default payout_method
        await prepare_payout_method_list(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        stripe_card = mock_stripe_card()
        payout_method_miscellaneous_create = PayoutMethodMiscellaneousCreate(
            payout_account_id=payment_account.id,
            payout_method_type=PayoutExternalAccountType.CARD.value,
            card=stripe_card,
        )
        payout_method, payout_card = await payout_method_miscellaneous_repo.unset_default_and_create_payout_method_and_payout_card(
            data=payout_method_miscellaneous_create
        )
        self.validate_results(stripe_card, payout_method, payout_card, payment_account)

        # the previous default payout_method list should be unset
        updated_payout_method_list = await payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=payment_account.id
        )
        assert updated_payout_method_list
        for pm in updated_payout_method_list:
            if pm.id != payout_method.id:
                assert not pm.is_default

    async def test_unset_default_and_create_payout_method_and_payout_card_failed_create_payout_card(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert a list of payout_method with 1 default payout_method
        payout_method_list = await prepare_payout_method_list(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        stripe_card = mock_stripe_card()
        stripe_card.fingerprint = None  # type: ignore
        payout_method_miscellaneous_create = PayoutMethodMiscellaneousCreate(
            payout_account_id=payment_account.id,
            payout_method_type=PayoutExternalAccountType.CARD.value,
            card=stripe_card,
        )

        with pytest.raises(ValidationError):
            await payout_method_miscellaneous_repo.unset_default_and_create_payout_method_and_payout_card(
                data=payout_method_miscellaneous_create
            )

        # the default payout_method for this payment account has not been changed
        actual_payout_method_list = await payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=payment_account.id
        )
        assert len(payout_method_list) == len(actual_payout_method_list)
        assert payout_method_list == actual_payout_method_list

    @staticmethod
    def validate_results(card, payout_method, payout_card, payment_account):
        assert payout_method
        assert payout_card
        # payout method
        assert payout_method.id == payout_card.id
        assert payout_method.created_at == payout_card.created_at
        assert payout_method.updated_at == payout_card.updated_at
        assert payout_method.payment_account_id == payment_account.id
        assert payout_method.is_default
        assert not payout_method.deleted_at
        # payout card
        assert payout_card.fingerprint == card.fingerprint
        assert payout_card.stripe_card_id == card.id
        assert payout_card.last4 == card.last4
        assert payout_card.brand == card.brand
        assert payout_card.exp_month == card.exp_month
        assert payout_card.exp_year == card.exp_year

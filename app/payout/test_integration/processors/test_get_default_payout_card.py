import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.payout.core.account.processors.get_default_payout_card import (
    GetDefaultPayoutCardRequest,
    GetDefaultPayoutCard,
)
from app.payout.core.account.types import PayoutCardInternal
from app.payout.core.exceptions import (
    PayoutErrorCode,
    payout_error_message_maps,
    PayoutError,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_payout_card_list,
    prepare_and_insert_payment_account,
    prepare_and_insert_payout_method,
    prepare_and_insert_payout_card,
)


class TestGetDefaultPayoutCard:
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

    async def test_get_default_payout_card(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        count = 4
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_card_list = await prepare_payout_card_list(
            payout_method_repo=payout_method_repo,
            payout_card_repo=payout_card_repo,
            payout_account_id=payout_account.id,
            count=count,
        )

        assert len(payout_card_list) == count
        request = GetDefaultPayoutCardRequest(payout_account_id=payout_account.id)

        default_payout_card = payout_card_list[0]
        default_payout_method = await payout_method_repo.get_payout_method_by_id(
            default_payout_card.id
        )
        assert default_payout_method
        expected_default_payout_card = PayoutCardInternal(
            stripe_card_id=default_payout_card.stripe_card_id,
            last4=default_payout_card.last4,
            brand=default_payout_card.brand,
            exp_month=default_payout_card.exp_month,
            exp_year=default_payout_card.exp_year,
            fingerprint=default_payout_card.fingerprint,
            payout_account_id=default_payout_method.payment_account_id,
            currency=default_payout_method.currency,
            country=default_payout_method.country,
            is_default=default_payout_method.is_default,
            id=default_payout_method.id,
            token=default_payout_method.token,
            created_at=default_payout_method.created_at,
            updated_at=default_payout_method.updated_at,
            deleted_at=default_payout_method.deleted_at,
        )

        get_default_payout_card_op = GetDefaultPayoutCard(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )

        actual_default_payout_card: PayoutCardInternal = await get_default_payout_card_op._execute()
        assert actual_default_payout_card.payout_account_id == payout_account.id
        assert actual_default_payout_card == expected_default_payout_card

    async def test_get_default_payout_card_no_payout_method_for_this_account(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        # default card doesn't exist
        fake_payout_account_id = 99999
        request = GetDefaultPayoutCardRequest(payout_account_id=fake_payout_account_id)

        get_default_payout_card_op = GetDefaultPayoutCard(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )
        with pytest.raises(PayoutError) as e:
            await get_default_payout_card_op._execute()

        assert e.value.error_code == PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND_FOR_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND_FOR_ACCOUNT.value
            ]
        )

    async def test_get_default_payout_card_no_payout_card_for_this_account(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo, payout_account_id=payout_account.id, is_default=True
        )
        assert payout_method
        request = GetDefaultPayoutCardRequest(payout_account_id=payout_account.id)

        get_default_payout_card_op = GetDefaultPayoutCard(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )
        with pytest.raises(PayoutError) as e:
            await get_default_payout_card_op._execute()

        assert e.value.error_code == PayoutErrorCode.PAYOUT_CARD_NOT_FOUND_FOR_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.PAYOUT_CARD_NOT_FOUND_FOR_ACCOUNT.value
            ]
        )

    async def test_get_default_payout_card_no_default_card(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_card = await prepare_and_insert_payout_card(
            payout_method_repo,
            payout_card_repo,
            payout_account_id=payout_account.id,
            is_default=False,
        )
        assert payout_card
        request = GetDefaultPayoutCardRequest(payout_account_id=payout_account.id)

        get_default_payout_card_op = GetDefaultPayoutCard(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )
        with pytest.raises(PayoutError) as e:
            await get_default_payout_card_op._execute()

        assert e.value.error_code == PayoutErrorCode.DEFAULT_PAYOUT_CARD_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.DEFAULT_PAYOUT_CARD_NOT_FOUND.value
            ]
        )

import pytest
import pytest_mock
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST

from app.commons.database.infra import DB
from app.payout.core.account.processors.get_payout_method import (
    GetPayoutMethodRequest,
    GetPayoutMethod,
)
from app.payout.core.account.types import PayoutCardInternal
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_payout_card,
    prepare_and_insert_payout_method,
)


class TestGetPayoutMethod:
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

    async def test_get_payout_method(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_card = await prepare_and_insert_payout_card(
            payout_method_repo, payout_card_repo, payout_account.id
        )
        payout_method = await payout_method_repo.get_payout_method_by_id(
            payout_method_id=payout_card.id
        )
        assert payout_method

        request = GetPayoutMethodRequest(
            payout_account_id=payout_account.id, payout_method_id=payout_method.id
        )

        get_payout_method_op = GetPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )

        expected_default_payout_card = PayoutCardInternal(
            stripe_card_id=payout_card.stripe_card_id,
            last4=payout_card.last4,
            brand=payout_card.brand,
            exp_month=payout_card.exp_month,
            exp_year=payout_card.exp_year,
            fingerprint=payout_card.fingerprint,
            payout_account_id=payout_method.payment_account_id,
            currency=payout_method.currency,
            country=payout_method.country,
            is_default=payout_method.is_default,
            id=payout_method.id,
            token=payout_method.token,
            created_at=payout_method.created_at,
            updated_at=payout_method.updated_at,
            deleted_at=payout_method.deleted_at,
        )
        payout_card_internal: PayoutCardInternal = await get_payout_method_op._execute()
        assert payout_card_internal.payout_account_id == payout_account.id
        assert payout_card_internal == expected_default_payout_card

    async def test_get_payout_method_throw_errors(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo, payout_account.id
        )

        # raise no payout_method for the given id
        request = GetPayoutMethodRequest(
            payout_account_id=payout_account.id, payout_method_id=(payout_method.id + 1)
        )

        get_payout_method_op_raise_no_payout_method = GetPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )

        with pytest.raises(PayoutError) as e:
            await get_payout_method_op_raise_no_payout_method._execute()
        assert e.value.status_code == HTTP_404_NOT_FOUND
        assert e.value.error_code == PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_METHOD_NOT_FOUND.value]
        )

        # raise no payout_card for the given payout_method id
        request = GetPayoutMethodRequest(
            payout_account_id=payout_account.id, payout_method_id=payout_method.id
        )

        get_payout_method_op_raise_no_payout_card = GetPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )

        with pytest.raises(PayoutError) as e:
            await get_payout_method_op_raise_no_payout_card._execute()
        assert e.value.status_code == HTTP_404_NOT_FOUND
        assert e.value.error_code == PayoutErrorCode.PAYOUT_CARD_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_CARD_NOT_FOUND.value]
        )

        # raise given payout_account id is not valid for the payout_method
        request = GetPayoutMethodRequest(
            payout_account_id=(payout_account.id + 1), payout_method_id=payout_method.id
        )

        get_payout_method_op_raise_account_not_match = GetPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            request=request,
        )

        with pytest.raises(PayoutError) as e:
            await get_payout_method_op_raise_account_not_match._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.PAYOUT_ACCOUNT_NOT_MATCH
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_ACCOUNT_NOT_MATCH.value]
        )

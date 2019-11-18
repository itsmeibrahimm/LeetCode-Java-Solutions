from typing import List

import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.commons.types import Currency, CountryCode
from app.payout.core.account.processors.list_payout_methods import (
    ListPayoutMethod,
    ListPayoutMethodRequest,
)
import app.payout.core.account.models as account_models
from app.payout.models import PayoutExternalAccountType
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_payout_card_list,
    prepare_and_insert_stripe_managed_account,
)


class TestListPayoutMethod:
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

    async def test_list_payout_method(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        # insert a stripe_managed_account
        stripe_managed_account = await prepare_and_insert_stripe_managed_account(
            payment_account_repo
        )
        assert stripe_managed_account

        payout_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo,
            account_id=stripe_managed_account.id,
        )
        payout_card_list = await prepare_payout_card_list(
            payout_method_repo, payout_card_repo, payout_account.id
        )
        assert payout_card_list

        request = ListPayoutMethodRequest(payout_account_id=payout_account.id)

        list_payout_method_op = ListPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payment_account_repo=payment_account_repo,
            request=request,
        )
        expected_card_list: List[account_models.PayoutCardInternal] = []
        for payout_card in payout_card_list:
            payout_method = await payout_method_repo.get_payout_method_by_id(
                payout_method_id=payout_card.id
            )
            assert payout_method
            expected_card_list.append(
                account_models.PayoutCardInternal(
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
            )
        expected_bank_account_internal = account_models.PayoutBankAccountInternal(
            payout_account_id=payout_account.id,
            currency=Currency.USD,
            country=CountryCode.US,
            bank_last4=stripe_managed_account.default_bank_last_four,
            bank_name=stripe_managed_account.default_bank_name,
            fingerprint=stripe_managed_account.fingerprint,
        )

        payout_method_list_internal = await list_payout_method_op._execute()
        assert expected_card_list == payout_method_list_internal.card_list
        assert payout_method_list_internal.bank_account_list == []

        # search for bank account only

        request_bank = ListPayoutMethodRequest(
            payout_account_id=payout_account.id,
            payout_method_type=PayoutExternalAccountType.BANK_ACCOUNT,
        )
        list_payout_method_bank_op = ListPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payment_account_repo=payment_account_repo,
            request=request_bank,
        )
        payout_method_list_bank_internal = await list_payout_method_bank_op._execute()
        assert payout_method_list_bank_internal.card_list == []
        assert [
            expected_bank_account_internal
        ] == payout_method_list_bank_internal.bank_account_list

    async def test_list_payout_method_with_limit(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_card_list = await prepare_payout_card_list(
            payout_method_repo, payout_card_repo, payout_account.id
        )
        assert payout_card_list

        limit = 2
        request = ListPayoutMethodRequest(
            payout_account_id=payout_account.id, limit=limit
        )

        list_payout_method_op = ListPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payment_account_repo=payment_account_repo,
            request=request,
        )
        expected_card_list: List[account_models.PayoutCardInternal] = []
        for payout_card in payout_card_list:
            payout_method = await payout_method_repo.get_payout_method_by_id(
                payout_method_id=payout_card.id
            )
            assert payout_method
            if len(expected_card_list) == limit:
                break
            expected_card_list.append(
                account_models.PayoutCardInternal(
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
            )

        payout_card_list_internal = await list_payout_method_op._execute()
        assert len(payout_card_list_internal.card_list) == limit
        assert expected_card_list == payout_card_list_internal.card_list

    async def test_list_payout_method_not_found(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)

        request = ListPayoutMethodRequest(payout_account_id=payout_account.id)

        list_payout_method_op_raise_no_payout_method = ListPayoutMethod(
            logger=mocker.Mock(),
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payment_account_repo=payment_account_repo,
            request=request,
        )

        payout_card_list_internal = (
            await list_payout_method_op_raise_no_payout_method._execute()
        )
        assert payout_card_list_internal.card_list == []

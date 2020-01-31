from datetime import datetime

import pytest

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

    async def test_create_payout_method(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_method, then validate
        await prepare_and_insert_payout_method(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )

    async def test_create_get_payout_method(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_method, then validate
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )

        assert payout_method == await payout_method_repo.get_payout_method_by_id(
            payout_method.id
        ), "retrieved payout method matches"

    async def test_update_payout_method_deleted_at_by_token(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_method, then validate
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        deleted_at = datetime.utcnow()
        updated_payout_method = await payout_method_repo.update_payout_method_deleted_at_by_token(
            token=payout_method.token, deleted_at=deleted_at
        )
        if updated_payout_method:
            assert (
                updated_payout_method.deleted_at == deleted_at
            ), "retrieved payout method matches"

    async def test_update_payout_method_deleted_at_by_payout_method_id(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert payout_method, then validate
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        deleted_at = datetime.utcnow()
        updated_payout_method = await payout_method_repo.update_payout_method_deleted_at_by_payout_method_id(
            payout_method_id=payout_method.id, deleted_at=deleted_at
        )
        if updated_payout_method:
            assert (
                updated_payout_method.deleted_at == deleted_at
            ), "retrieved payout method matches"

    async def test_list_payout_method_by_payment_account_id(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert a list of payout_method, then validate
        payout_method_list = await prepare_payout_method_list(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        retrieved_payout_account_list = await payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=payment_account.id
        )
        assert (
            payout_method_list == retrieved_payout_account_list
        ), "retrieved payout method list matches"

    async def test_unset_default_payout_method_for_payout_account(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_card_repo: PayoutCardRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        # prepare and insert a list of payout_method with 1 default payout_method
        payout_method_list = await prepare_payout_method_list(
            payout_method_repo=payout_method_repo, payout_account_id=payment_account.id
        )
        # add another default payout_method for the same payout account
        payout_method = await prepare_and_insert_payout_method(
            payout_method_repo=payout_method_repo,
            payout_account_id=payment_account.id,
            is_default=True,
        )
        payout_method_list.append(payout_method)
        assert payout_method_list
        updated_payout_account_list = await payout_method_repo.unset_default_payout_method_for_payout_account(
            payout_account_id=payment_account.id
        )
        assert len(payout_method_list) == len(
            updated_payout_account_list
        ), "updated payout method list size matches with expected"
        for payout_method in updated_payout_account_list:
            assert (
                not payout_method.is_default
            ), "payout method has been set to non-default"

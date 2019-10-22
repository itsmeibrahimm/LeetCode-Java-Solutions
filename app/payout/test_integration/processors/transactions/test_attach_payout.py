from typing import List

import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.core.transaction.processors.attach_payout import (
    AttachPayoutRequest,
    AttachPayout,
    ERROR_MSG_TRANSACTION_HAS_TRANSFER_ID_CANNOT_BE_ATTACHED_TO_PAYOUT_ID,
    ERROR_MSG_INPUT_CONTAIN_INVALID_TRANSACTION,
)
from app.payout.core.transaction.models import (
    TransactionListInternal,
    TransactionInternal,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction_list_for_same_account,
    prepare_and_insert_payout,
)
import app.payout.core.transaction.utils as utils


class TestAttachPayout:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    async def test_attach_payout(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare test data:
        # - create a payout_account and a transaction list
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        count = 3
        transactions = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            count=count,
        )
        # - create a payout
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # 1. attach a payout_id to the transactions
        transaction_ids = [transaction.id for transaction in transactions]
        attach_payout_request = AttachPayoutRequest(
            transaction_ids=transaction_ids, payout_id=payout.id
        )
        attach_payout_op = AttachPayout(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=attach_payout_request,
        )
        updated_transaction_list_internal = await attach_payout_op._execute()
        expected_transaction_list: List[TransactionInternal] = [
            utils.to_transaction_internal(transaction) for transaction in transactions
        ]
        for transaction in expected_transaction_list:
            transaction.payout_id = payout.id
        expected_transaction_list_internal = TransactionListInternal(
            data=expected_transaction_list, count=len(expected_transaction_list)
        )
        TestAttachPayout._validate_updated_transactions(
            updated_transaction_list_internal, expected_transaction_list_internal
        )

        # 2. detach transaction list from payout id
        detach_payout_request = AttachPayoutRequest(transaction_ids=transaction_ids)
        detach_payout_op = AttachPayout(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=detach_payout_request,
        )
        detach_payout_transaction_list_internal = await detach_payout_op._execute()
        expected_detached_transaction_list: List[TransactionInternal] = [
            utils.to_transaction_internal(transaction) for transaction in transactions
        ]
        for transaction in expected_detached_transaction_list:
            transaction.payout_id = None
        expected_detached_transaction_list_internal = TransactionListInternal(
            data=expected_detached_transaction_list,
            count=len(expected_detached_transaction_list),
        )
        TestAttachPayout._validate_updated_transactions(
            detach_payout_transaction_list_internal,
            expected_detached_transaction_list_internal,
        )

        # 3. attach for a non-exist transaction should raise error
        largest_txn_id = transaction_ids[0]
        attach_non_exist_request = AttachPayoutRequest(
            transaction_ids=[largest_txn_id + 1]
        )
        attach_non_exist_op = AttachPayout(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=attach_non_exist_request,
        )
        with pytest.raises(PayoutError) as e:
            await attach_non_exist_op._execute()
        assert e.value.error_code == PayoutErrorCode.TRANSACTION_INVALID
        assert e.value.error_message == ERROR_MSG_INPUT_CONTAIN_INVALID_TRANSACTION

        # 4. attach a transaction which already have transfer_id should raise error
        transaction_with_transfer_id = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            transfer_id=1,
            count=1,
        )
        attach_payout_with_transfer_id_request_error = AttachPayoutRequest(
            transaction_ids=[transaction_with_transfer_id[0].id]
        )
        attach_payout_with_transfer_id_error_op = AttachPayout(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=attach_payout_with_transfer_id_request_error,
        )
        with pytest.raises(PayoutError) as e:
            await attach_payout_with_transfer_id_error_op._execute()
        assert e.value.error_code == PayoutErrorCode.TRANSACTION_INVALID
        assert (
            e.value.error_message
            == ERROR_MSG_TRANSACTION_HAS_TRANSFER_ID_CANNOT_BE_ATTACHED_TO_PAYOUT_ID
        )

    @staticmethod
    def _validate_updated_transactions(
        actual_transaction_list_internal: TransactionListInternal,
        expected_transaction_list_internal: TransactionListInternal,
    ):
        assert (
            actual_transaction_list_internal.count
            == expected_transaction_list_internal.count
        ), "The count of updated transaction list should match with expected count"
        for i in range(0, actual_transaction_list_internal.count):
            assert (
                actual_transaction_list_internal.data[i].id
                == expected_transaction_list_internal.data[i].id
            ), "id should match"
            assert (
                actual_transaction_list_internal.data[i].payout_id
                == expected_transaction_list_internal.data[i].payout_id
            ), "payout_id should have been updated"
            assert (
                actual_transaction_list_internal.data[i].amount
                == expected_transaction_list_internal.data[i].amount
            ), "amount should match"

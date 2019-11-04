import json

import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.core.transaction.processors.reverse_transaction import (
    ReverseTransactionRequest,
    ReverseTransaction,
    ERROR_MSG_TRANSACTION_ALREADY_CANCELLED,
    ERROR_MSG_TRANSACTION_NOT_EXIST_FOR_REVERSE,
)
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
)
import app.payout.core.transaction.utils as utils
from app.payout.models import TransactionState


class TestReverseTransactions:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    async def test_reverse_transaction(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
    ):
        # prepare test data:
        # - create a payout_account and a transaction
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account.id
        )

        # 1. reverse transaction should return a transaction with negative amount and amount_paid
        reverse_transaction_request = ReverseTransactionRequest(
            transaction_id=transaction.id
        )
        reverse_transaction_op = ReverseTransaction(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=reverse_transaction_request,
        )
        actual_transaction_internal = await reverse_transaction_op._execute()
        expected_transaction = TransactionDBEntity(
            id=actual_transaction_internal.id,
            payment_account_id=transaction.payment_account_id,
            amount=transaction.amount * -1,
            amount_paid=transaction.amount_paid * -1,
            currency=transaction.currency,
            target_id=transaction.target_id,
            target_type=transaction.target_type,
            metadata=json.dumps(
                ReverseTransaction.metadata_for_reversal(transaction.id)
            ),
            idempotency_key=ReverseTransaction.idempotency_key_for_reversal(
                transaction.id
            ),
            created_at=actual_transaction_internal.created_at,
            updated_at=actual_transaction_internal.updated_at,
        )
        expected_transaction_internal = utils.get_transaction_internal_from_db_entity(
            expected_transaction
        )
        assert (
            expected_transaction_internal == actual_transaction_internal
        ), "retrieved transaction_list_internal should match with expected for reverse transaction"

        # 2. reverse a transaction with a reason
        expected_reverse_reason = "test_reverse_reason"
        transaction_with_reverse_reason = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account.id
        )
        reverse_transaction_with_reason_request = ReverseTransactionRequest(
            transaction_id=transaction_with_reverse_reason.id,
            reverse_reason=expected_reverse_reason,
        )
        reverse_transaction_with_reason_op = ReverseTransaction(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=reverse_transaction_with_reason_request,
        )
        actual_reversed_transaction_with_reason_internal = (
            await reverse_transaction_with_reason_op._execute()
        )
        expected_reversed_transaction_with_reason = TransactionDBEntity(
            id=actual_reversed_transaction_with_reason_internal.id,
            payment_account_id=transaction_with_reverse_reason.payment_account_id,
            amount=transaction_with_reverse_reason.amount * -1,
            amount_paid=transaction_with_reverse_reason.amount_paid * -1,
            currency=transaction_with_reverse_reason.currency,
            target_id=transaction_with_reverse_reason.target_id,
            target_type=transaction_with_reverse_reason.target_type,
            metadata=json.dumps(
                ReverseTransaction.metadata_for_reversal(
                    transaction_with_reverse_reason.id, expected_reverse_reason
                )
            ),
            idempotency_key=ReverseTransaction.idempotency_key_for_reversal(
                transaction_with_reverse_reason.id
            ),
            created_at=actual_reversed_transaction_with_reason_internal.created_at,
            updated_at=actual_reversed_transaction_with_reason_internal.updated_at,
        )
        expected_transaction_with_reason_internal = utils.get_transaction_internal_from_db_entity(
            expected_reversed_transaction_with_reason
        )
        assert (
            expected_transaction_with_reason_internal
            == actual_reversed_transaction_with_reason_internal
        ), "reverse a transaction with a reverse reason should match with expected for reverse transaction"

        # 3. reverse for a non-exist transaction should raise error
        reverse_transaction_request_error = ReverseTransactionRequest(
            transaction_id=transaction_with_reverse_reason.id + 2
        )
        reverse_transaction_error_op = ReverseTransaction(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=reverse_transaction_request_error,
        )
        with pytest.raises(PayoutError) as e:
            await reverse_transaction_error_op._execute()
        assert e.value.error_code == PayoutErrorCode.TRANSACTION_INVALID
        assert e.value.error_message == ERROR_MSG_TRANSACTION_NOT_EXIST_FOR_REVERSE

        # 4. reverse a cancelled transaction should raise error
        cancelled_transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            state=TransactionState.CANCELLED,
        )
        reverse_cancelled_transaction_request_error = ReverseTransactionRequest(
            transaction_id=cancelled_transaction.id
        )
        reverse_cancelled_transaction_error_op = ReverseTransaction(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=reverse_cancelled_transaction_request_error,
        )
        with pytest.raises(PayoutError) as e:
            await reverse_cancelled_transaction_error_op._execute()
        assert e.value.error_code == PayoutErrorCode.TRANSACTION_INVALID
        assert e.value.error_message == ERROR_MSG_TRANSACTION_ALREADY_CANCELLED

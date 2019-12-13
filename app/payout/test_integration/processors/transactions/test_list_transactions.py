from typing import List

import pytest
import pytest_mock

from app.commons.test_integration.constants import TEST_DEFAULT_PAGE_SIZE
from app.commons.types import Currency
from app.payout.core.transaction.processors.list_transactions import (
    ListTransactionsRequest,
    ListTransactions,
)
from app.payout.core.transaction.models import (
    TransactionListInternal,
    TransactionInternal,
)
from app.payout.repository.bankdb.model.transaction import (
    TransactionDBEntity,
    TransactionCreateDBEntity,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction_list_for_same_account,
    prepare_and_insert_transaction_list_for_different_targets,
    prepare_and_insert_transfer,
    prepare_and_insert_payout,
    prepare_and_insert_paid_transaction_list_for_transfer,
)
import app.payout.models as payout_models


class TestListTransactions:
    pytestmark = [pytest.mark.asyncio]

    async def test_list_transactions_by_ids(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
    ):
        # prepare test data:
        # - create a payout_account
        # - total 10 transactions created for the same account
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        transaction_list = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo, payout_account_id=payout_account.id
        )
        # prepare a list of transaction ids to filter
        transaction_ids = [transaction.id for transaction in transaction_list]

        # 1. filter by transaction_ids without passing limit
        request_by_transaction_ids = ListTransactionsRequest(
            transaction_ids=transaction_ids
        )
        list_by_transaction_ids_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_transaction_ids,
        )
        expected_transaction_list_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in transaction_list
            ],
            count=len(transaction_list),
            new_offset=len(transaction_list),
        )
        actual_transaction_list_internal = await list_by_transaction_ids_op._execute()
        assert (
            expected_transaction_list_internal == actual_transaction_list_internal
        ), "retrieved transaction_list_internal should match with expected for filtering by transaction ids"

    async def test_list_transactions_by_target_ids_and_type(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
    ):
        # prepare test data:
        # - total 30 transactions created for the same account
        # - total 5 payout accounts created with 5 target ids and 2 target types
        transaction_list, target_id_list = await prepare_and_insert_transaction_list_for_different_targets(
            transaction_repo=transaction_repo, payment_account_repo=payment_account_repo
        )
        expected_list_for_dasher_delivery: List[TransactionDBEntity] = []
        expected_list_for_dasher_job: List[TransactionDBEntity] = []
        for transaction in transaction_list:
            if (
                transaction.target_type
                == payout_models.TransactionTargetType.DASHER_DELIVERY.value
            ):
                expected_list_for_dasher_delivery.append(transaction)
            else:
                expected_list_for_dasher_job.append(transaction)

        # 1. filter by target_ids and "dasher" with offset = 0 and limit = 10
        expected_list_for_dasher_first_page: List[
            TransactionDBEntity
        ] = expected_list_for_dasher_delivery[:TEST_DEFAULT_PAGE_SIZE]
        offset = 0
        new_offset = offset + len(expected_list_for_dasher_first_page)
        expected_transaction_list_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_list_for_dasher_first_page
            ],
            new_offset=new_offset,
            count=len(expected_list_for_dasher_first_page),
        )
        request_by_target_ids_and_type = ListTransactionsRequest(
            target_ids=target_id_list,
            target_type=payout_models.TransactionTargetType.DASHER_DELIVERY,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_target_ids_and_type_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_target_ids_and_type,
        )
        actual_list_by_target_ids_and_type = (
            await list_by_target_ids_and_type_op._execute()
        )
        assert actual_list_by_target_ids_and_type
        assert (
            expected_transaction_list_internal == actual_list_by_target_ids_and_type
        ), "filter by target ids and type should match with expected"

        # 2. filter by target_ids and "dasher" with offset = 10 and limit = 10
        expected_list_for_dasher_sec_page: List[
            TransactionDBEntity
        ] = expected_list_for_dasher_delivery[TEST_DEFAULT_PAGE_SIZE:]
        offset = len(expected_list_for_dasher_first_page)
        new_offset = offset + len(expected_list_for_dasher_sec_page)
        expected_transaction_list_internal_sec_page = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_list_for_dasher_sec_page
            ],
            new_offset=new_offset,
            count=len(expected_list_for_dasher_sec_page),
        )
        request_by_target_ids_and_type_sec_page = ListTransactionsRequest(
            target_ids=target_id_list,
            target_type=payout_models.TransactionTargetType.DASHER_DELIVERY,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_target_ids_and_type_op_sec_page = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_target_ids_and_type_sec_page,
        )
        actual_list_by_target_ids_and_type_sec_page = (
            await list_by_target_ids_and_type_op_sec_page._execute()
        )
        assert actual_list_by_target_ids_and_type_sec_page
        assert (
            expected_transaction_list_internal_sec_page
            == actual_list_by_target_ids_and_type_sec_page
        ), "retrieved list by target ids and type should match with expected for second page"

        # 3. validate total count is equal the sum of first page plus second page
        total = (
            actual_list_by_target_ids_and_type.count
            + actual_list_by_target_ids_and_type_sec_page.count
        )
        assert total == len(expected_list_for_dasher_delivery), (
            "total transaction number for dasher should be the sum of "
            "first page and second page"
        )

    async def test_list_transactions_by_transfer_id(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare test data:
        # - create a payout_account
        # - prepare 2 transfers
        # - 4 transactions created for transfer_a; 13 transactions created for transfer_b
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        transfer_a = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_b = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        count_a = 4
        count_b = 13
        transaction_list_a = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            transfer_id=transfer_a.id,
            count=count_a,
        )
        transaction_list_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            transfer_id=transfer_b.id,
            count=count_b,
        )

        # 1. filter by transfer_id_a with offset = 0 and limit = 10
        expected_list_by_transfer_id_a_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in transaction_list_a
            ],
            new_offset=len(transaction_list_a),
            count=len(transaction_list_a),
        )

        offset = 0
        request_by_transfer_id_a = ListTransactionsRequest(
            transfer_id=transfer_a.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_transfer_id_a = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_transfer_id_a,
        )
        actual_list_by_transfer_id_a = await list_by_transfer_id_a._execute()
        assert actual_list_by_transfer_id_a
        assert (
            expected_list_by_transfer_id_a_internal == actual_list_by_transfer_id_a
        ), "filter by transfer id should match with expected"

        # 2. filter by transfer_id_b with offset = 0 and limit = 10
        offset = 0
        expected_transaction_list_b_first_page = transaction_list_b[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        expected_list_by_transfer_id_b_internal_first_page = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_b_first_page
            ],
            new_offset=TEST_DEFAULT_PAGE_SIZE,
            count=TEST_DEFAULT_PAGE_SIZE,
        )
        request_by_transfer_id_b_first_page = ListTransactionsRequest(
            transfer_id=transfer_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_transfer_id_b_first_page = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_transfer_id_b_first_page,
        )
        actual_list_by_transfer_id_b_first_page = (
            await list_by_transfer_id_b_first_page._execute()
        )
        assert actual_list_by_transfer_id_b_first_page
        assert (
            expected_list_by_transfer_id_b_internal_first_page
            == actual_list_by_transfer_id_b_first_page
        ), "filter by transfer id for first page should match with expected"

        # 3. filter by transfer_id_b with offset = 10 and limit = 10
        offset = len(expected_transaction_list_b_first_page)
        expected_transaction_list_b_sec_page = transaction_list_b[
            TEST_DEFAULT_PAGE_SIZE:
        ]
        expected_list_by_transfer_id_b_internal_sec_page = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_b_sec_page
            ],
            new_offset=offset + len(expected_transaction_list_b_sec_page),
            count=len(expected_transaction_list_b_sec_page),
        )
        request_by_transfer_id_b_sec_page = ListTransactionsRequest(
            transfer_id=transfer_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_transfer_id_b_sec_page = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_transfer_id_b_sec_page,
        )
        actual_list_by_transfer_id_b_sec_page = (
            await list_by_transfer_id_b_sec_page._execute()
        )
        assert actual_list_by_transfer_id_b_sec_page
        assert (
            expected_list_by_transfer_id_b_internal_sec_page
            == actual_list_by_transfer_id_b_sec_page
        ), "filter by transfer id for second page should match with expected"

        # 4. validate total amount for transfer_b
        total = (
            actual_list_by_transfer_id_b_first_page.count
            + actual_list_by_transfer_id_b_sec_page.count
        )
        assert total == len(transaction_list_b), (
            "total count of stream transaction by transfer_id_b should match "
            "with total number of transaction created by transfer_b"
        )

    async def test_list_transactions_by_payout_id(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare test data:
        # - create a payout_account
        # - prepare 2 payouts
        # - 4 transactions created for transfer_a; 13 transactions created for transfer_b
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        payout_a = await prepare_and_insert_payout(payout_repo=payout_repo)
        payout_b = await prepare_and_insert_payout(payout_repo=payout_repo)
        count_a = 4
        count_b = 13
        transaction_list_a = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            payout_id=payout_a.id,
            count=count_a,
        )
        transaction_list_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            payout_id=payout_b.id,
            count=count_b,
        )

        # 1. filter by payout_id_a with offset = 0 and limit = 10
        expected_list_by_payout_id_a_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in transaction_list_a
            ],
            new_offset=len(transaction_list_a),
            count=len(transaction_list_a),
        )

        offset = 0
        request_by_payout_id_a = ListTransactionsRequest(
            payout_id=payout_a.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_payout_id_a = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_id_a,
        )
        actual_list_by_payout_id_a = await list_by_payout_id_a._execute()
        assert actual_list_by_payout_id_a
        assert (
            expected_list_by_payout_id_a_internal == actual_list_by_payout_id_a
        ), "filter by payout id should match with expected"

        # 2. filter by payout_id_b with offset = 0 and limit = 10
        offset = 0
        expected_transaction_list_b_first_page = transaction_list_b[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        expected_list_by_payout_id_b_internal_first_page = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_b_first_page
            ],
            new_offset=TEST_DEFAULT_PAGE_SIZE,
            count=TEST_DEFAULT_PAGE_SIZE,
        )
        request_by_payout_id_b_first_page = ListTransactionsRequest(
            payout_id=payout_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_payout_id_b_first_page = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_id_b_first_page,
        )
        actual_list_by_payout_id_b_first_page = (
            await list_by_payout_id_b_first_page._execute()
        )
        assert actual_list_by_payout_id_b_first_page
        assert (
            expected_list_by_payout_id_b_internal_first_page
            == actual_list_by_payout_id_b_first_page
        ), "filter by payout id for first page should match with expected"

        # 3. filter by payout_id_b with offset = 10 and limit = 10
        offset = len(expected_transaction_list_b_first_page)
        expected_transaction_list_b_sec_page = transaction_list_b[
            TEST_DEFAULT_PAGE_SIZE:
        ]
        expected_list_by_payout_id_b_internal_sec_page = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_b_sec_page
            ],
            new_offset=offset + len(expected_transaction_list_b_sec_page),
            count=len(expected_transaction_list_b_sec_page),
        )
        request_by_payout_id_b_sec_page = ListTransactionsRequest(
            payout_id=payout_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        list_by_payout_id_b_sec_page = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_id_b_sec_page,
        )
        actual_list_by_payout_id_b_sec_page = (
            await list_by_payout_id_b_sec_page._execute()
        )
        assert actual_list_by_payout_id_b_sec_page
        assert (
            expected_list_by_payout_id_b_internal_sec_page
            == actual_list_by_payout_id_b_sec_page
        ), "filter by transfer id for second page should match with expected"

        # 4. validate total amount for transfer_b
        total = (
            actual_list_by_payout_id_b_first_page.count
            + actual_list_by_payout_id_b_sec_page.count
        )
        assert total == len(transaction_list_b), (
            "total count of stream transaction by payout_id_b should match with "
            "total number of transaction created by transfer_b"
        )

    async def test_list_transactions_by_payout_account_id(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare test data:
        # - create a payout_account
        # - 30 transactions created for this payout_account
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        total = 30
        transaction_list = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            count=total,
        )

        # 1. filter by payout account id without time_range with offset=0 and limit = 10
        offset = 0
        expected_transaction_list_first_page_without_time_range = transaction_list[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        expected_transaction_list_first_page_without_time_range_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_first_page_without_time_range
            ],
            new_offset=offset
            + len(expected_transaction_list_first_page_without_time_range),
            count=len(expected_transaction_list_first_page_without_time_range),
        )
        request_by_payout_account_id_without_time_range = ListTransactionsRequest(
            payout_account_id=payout_account.id,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_payout_account_id_without_time_range_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_account_id_without_time_range,
        )
        actual_transaction_list_first_page_without_time_range_internal = (
            await list_by_payout_account_id_without_time_range_op._execute()
        )
        assert actual_transaction_list_first_page_without_time_range_internal
        assert (
            expected_transaction_list_first_page_without_time_range_internal
            == actual_transaction_list_first_page_without_time_range_internal
        ), "filter by payout account id without time range for second page should match with expected"

        # 2. filter by payout account id with time_range with offset=0 and limit = 10
        expected_count = 8
        expected_transaction_list_first_page_with_time_range = transaction_list[
            TEST_DEFAULT_PAGE_SIZE : TEST_DEFAULT_PAGE_SIZE + expected_count
        ]
        end_time = expected_transaction_list_first_page_with_time_range[0].created_at
        start_time = expected_transaction_list_first_page_with_time_range[
            expected_count - 1
        ].created_at

        expected_transaction_list_first_page_with_time_range_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_first_page_with_time_range
            ],
            new_offset=offset
            + len(expected_transaction_list_first_page_with_time_range),
            count=len(expected_transaction_list_first_page_with_time_range),
        )
        request_by_payout_account_id_with_time_range = ListTransactionsRequest(
            payout_account_id=payout_account.id,
            time_range=payout_models.TimeRange(
                start_time=start_time, end_time=end_time
            ),
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_payout_account_id_with_time_range_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_account_id_with_time_range,
        )
        actual_transaction_list_first_page_with_time_range_internal = (
            await list_by_payout_account_id_with_time_range_op._execute()
        )
        assert actual_transaction_list_first_page_without_time_range_internal
        assert (
            expected_transaction_list_first_page_with_time_range_internal
            == actual_transaction_list_first_page_with_time_range_internal
        ), "filter by payout account id with time range for second page should match with expected"

        # 3. filter by payout account id with start_time and offset=0, limit = 10
        offset = 0
        expected_transaction_list_first_page_with_start_time = transaction_list[:10]
        expected_count = len(expected_transaction_list_first_page_with_start_time)
        start_time = transaction_list[expected_count + 5].created_at
        expected_transaction_list_first_page_with_start_time_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_first_page_with_start_time
            ],
            new_offset=offset
            + len(expected_transaction_list_first_page_with_start_time),
            count=TEST_DEFAULT_PAGE_SIZE,
        )
        request_by_payout_account_id_with_start_time = ListTransactionsRequest(
            payout_account_id=payout_account.id,
            time_range=payout_models.TimeRange(start_time=start_time, end_time=None),
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_payout_account_id_with_start_time_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_account_id_with_start_time,
        )
        actual_transaction_list_first_page_with_start_time_internal = (
            await list_by_payout_account_id_with_start_time_op._execute()
        )
        assert actual_transaction_list_first_page_with_start_time_internal
        assert (
            expected_transaction_list_first_page_with_start_time_internal
            == actual_transaction_list_first_page_with_start_time_internal
        ), "filter by payout account id with start time should match with expected"

    async def test_list_unpaid_transactions_by_payout_account_id(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare test data:
        # - create a payout_account
        # - 30 transactions created for this payout_account
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        count = 6
        transaction_list_unpaid = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            count=count,
        )
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_paid_transaction_list_for_transfer(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account.id,
            transfer_id=transfer.id,
            count=count,
        )

        # 1. filter unpaid transaction list by payout account id with offset=0 and limit=10
        offset = 0
        expected_transaction_list_unpaid = transaction_list_unpaid[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        expected_count = len(transaction_list_unpaid)
        expected_transaction_list_unpaid_internal = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_unpaid
            ],
            new_offset=offset + len(expected_transaction_list_unpaid),
            count=expected_count,
        )
        request_by_payout_account_id_unpaid = ListTransactionsRequest(
            payout_account_id=payout_account.id,
            unpaid=True,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_payout_account_id_unpaid_op = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_account_id_unpaid,
        )
        actual_transaction_list_unpaid_internal = (
            await list_by_payout_account_id_unpaid_op._execute()
        )
        assert actual_transaction_list_unpaid_internal
        assert (
            expected_transaction_list_unpaid_internal
            == actual_transaction_list_unpaid_internal
        ), "filter unpaid by payout account id with offset and limit should match with expected"

        # 2. insert another unpaid transaction with state is ACTIVE
        data = TransactionCreateDBEntity(
            amount=1000,
            amount_paid=800,
            payment_account_id=payout_account.id,
            currency=Currency.USD.value,
            state=payout_models.TransactionState.ACTIVE.value,
        )
        unpaid_transaction = await transaction_repo.create_transaction(data)

        # 3. get unpaid transaction list again
        expected_transaction_list_unpaid.insert(0, unpaid_transaction)
        expected_count = expected_count + 1
        expected_transaction_list_unpaid_internal_b = TransactionListInternal(
            data=[
                TransactionInternal(
                    **transaction.dict(),
                    payout_account_id=transaction.payment_account_id
                )
                for transaction in expected_transaction_list_unpaid
            ],
            new_offset=offset + len(expected_transaction_list_unpaid),
            count=expected_count,
        )
        request_by_payout_account_id_unpaid_b = ListTransactionsRequest(
            payout_account_id=payout_account.id,
            unpaid=True,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        list_by_payout_account_id_unpaid_op_b = ListTransactions(
            logger=mocker.Mock(),
            transaction_repo=transaction_repo,
            request=request_by_payout_account_id_unpaid_b,
        )
        actual_transaction_list_unpaid_internal_b = (
            await list_by_payout_account_id_unpaid_op_b._execute()
        )
        assert actual_transaction_list_unpaid_internal_b
        assert (
            expected_transaction_list_unpaid_internal_b
            == actual_transaction_list_unpaid_internal_b
        ), "filter unpaid by payout account id with offset and limit should match with expected"

from typing import List

import pytest

from app.commons.database.infra import DB
from app.commons.test_integration.constants import TEST_DEFAULT_PAGE_SIZE
from app.payout.repository.bankdb.model.transaction import (
    TransactionUpdateDBEntity,
    TransactionDBEntity,
    TransactionCreateDBEntity,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transaction,
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction_list_for_same_account,
    prepare_and_insert_transaction_list_for_different_targets,
    prepare_and_insert_payout,
    prepare_and_insert_transfer,
    prepare_and_insert_paid_transaction_list_for_transfer,
)
from app.payout import types
from app.payout.types import PayoutAccountTargetType, TransactionState


class TestTransactionRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    async def payout_account_id(
        self, payment_account_repo: PaymentAccountRepository
    ) -> types.PayoutAccountId:
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        return payment_account.id

    async def test_create_transaction(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )

    async def test_create_get_transaction(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )
        assert transaction == await transaction_repo.get_transaction_by_id(
            transaction.id
        ), "retrieved transaction matches"

    async def test_update_transaction_by_id(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )
        new_data = TransactionUpdateDBEntity(
            amount=10000, payment_account_id=123, amount_paid=8000
        )

        updated_row = await transaction_repo.update_transaction_by_id(
            transaction.id, new_data
        )
        assert updated_row, "updated row"
        assert updated_row.id == transaction.id, "updated expected row"
        assert new_data.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ) == updated_row.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ), "updated content ok"

    async def test_set_transaction_payout_id_by_ids(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        first_txn = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )
        second_txn = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )
        transaction_ids = [first_txn.id, second_txn.id]

        new_payout_id = 101
        updated_rows = await transaction_repo.set_transaction_payout_id_by_ids(
            transaction_ids, payout_id=new_payout_id
        )
        assert updated_rows, "updated"
        assert len(updated_rows) == 2, "both rows updated"
        for row in updated_rows:
            assert row.payout_id == new_payout_id, "payout id updated"

    async def test_get_transaction_by_ids(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # 1. add 10 transaction for the same account and do a get by ids should return
        # all the transactions
        transaction_list = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )
        transaction_ids = [transaction.id for transaction in transaction_list]

        # get a list fewer than one default page size
        retrieved_transaction_list = await transaction_repo.get_transaction_by_ids(
            transaction_ids
        )
        assert len(retrieved_transaction_list) == len(
            transaction_ids
        ), "get transaction list size matches with expected size"
        assert (
            retrieved_transaction_list == transaction_list
        ), "retrieved transaction list matches with expected list"

        # 2. add another 5 transactions for the same account and do a get by ids should
        # return all transactions
        transaction_list_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            count=5,
        )
        for transaction in transaction_list:
            transaction_list_b.append(transaction)
        transaction_ids_b = [transaction.id for transaction in transaction_list_b]
        retrieved_transaction_list_b = await transaction_repo.get_transaction_by_ids(
            transaction_ids_b
        )
        assert len(retrieved_transaction_list_b) == len(
            transaction_list_b
        ), "get transaction list size matches with expected size"
        assert (
            retrieved_transaction_list_b == transaction_list_b
        ), "retrieved transaction list matches with expected list"

    async def test_get_transaction_by_ids_return_emtpy(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transaction_ids: List[int] = []
        retrieved_transaction_list = await transaction_repo.get_transaction_by_ids(
            transaction_ids
        )
        assert (
            retrieved_transaction_list == []
        ), "filter by an empty transaction id list should return an empty list"

        non_exist_transaction_ids = [-1]
        retrieved_transaction_list_non_exist = await transaction_repo.get_transaction_by_ids(
            non_exist_transaction_ids
        )
        assert retrieved_transaction_list_non_exist == [], (
            "filter by an non-exist transaction id list should return " "an empty list"
        )

    async def test_get_transaction_by_target_ids_and_type(
        self,
        transaction_repo: TransactionRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transaction_list, target_id_list = await prepare_and_insert_transaction_list_for_different_targets(
            transaction_repo=transaction_repo, payment_account_repo=payment_account_repo
        )

        # get the first page of the total amount
        expected_list_for_dasher: List[TransactionDBEntity] = []
        expected_list_for_store: List[TransactionDBEntity] = []
        for transaction in transaction_list:
            if transaction.target_type == PayoutAccountTargetType.DASHER.value:
                expected_list_for_dasher.append(transaction)
            else:
                expected_list_for_store.append(transaction)

        # first page
        expected_list_for_dasher_first_page: List[
            TransactionDBEntity
        ] = expected_list_for_dasher[:TEST_DEFAULT_PAGE_SIZE]
        offset = 0
        retrieved_transaction_list_for_dasher_first_page = await transaction_repo.get_transaction_by_target_ids_and_type(
            target_ids=target_id_list,
            target_type=PayoutAccountTargetType.DASHER.value,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert len(retrieved_transaction_list_for_dasher_first_page) == len(
            expected_list_for_dasher_first_page
        ), "get transaction list size matches with expected size"
        assert (
            retrieved_transaction_list_for_dasher_first_page
            == expected_list_for_dasher_first_page
        ), "retrieved transaction list matches with expected list"

        # second page
        expected_list_for_dasher_sec_page: List[
            TransactionDBEntity
        ] = expected_list_for_dasher[TEST_DEFAULT_PAGE_SIZE:]
        offset = offset + len(retrieved_transaction_list_for_dasher_first_page)
        retrieved_transaction_list_for_dasher_sec_page = await transaction_repo.get_transaction_by_target_ids_and_type(
            target_ids=target_id_list,
            target_type=PayoutAccountTargetType.DASHER.value,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert len(retrieved_transaction_list_for_dasher_sec_page) == len(
            expected_list_for_dasher_sec_page
        ), "get transaction list size matches with expected size"
        assert (
            retrieved_transaction_list_for_dasher_sec_page
            == expected_list_for_dasher_sec_page
        ), "retrieved transaction list matches with expected list"

        # validate total amount
        total = len(retrieved_transaction_list_for_dasher_first_page) + len(
            retrieved_transaction_list_for_dasher_sec_page
        )
        assert total == len(expected_list_for_dasher), (
            "total transaction number for dasher should be the sum of "
            "first page and second page"
        )

    async def test_get_transaction_by_target_ids_and_type_return_empty(
        self,
        transaction_repo: TransactionRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        # filter by invalid type
        retrieved_transaction_list_invalid_target_type = await transaction_repo.get_transaction_by_target_ids_and_type(
            target_ids=[1, 2, 3],
            target_type="invalid_target_type",
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert retrieved_transaction_list_invalid_target_type == [], (
            "filtering by invalid target type should return" "an empty transaction list"
        )

        # filter by invalid target ids
        retrieved_transaction_list_invalid_target_ids = await transaction_repo.get_transaction_by_target_ids_and_type(
            target_ids=[-1, 0],
            target_type="dasher",
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert retrieved_transaction_list_invalid_target_ids == [], (
            "filtering by invalid target ids should return " "an empty transaction list"
        )

    async def test_get_transaction_by_transfer_id(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transfer_a = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_b = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        count_a = 4
        count_b = 13
        transaction_list_a = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer_a.id,
            count=count_a,
        )
        transaction_list_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer_b.id,
            count=count_b,
        )

        # get the first page for transfer a
        offset = 0
        retrieved_transaction_list_a = await transaction_repo.get_transaction_by_transfer_id(
            transfer_id=transfer_a.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_transaction_list_a) == len(
            transaction_list_a
        ), "get transaction list by transfer id size should match with expected size"
        assert (
            retrieved_transaction_list_a == transaction_list_a
        ), "retrieved transaction list by transfer id should match with expected list"

        # get the first page for transfer b
        offset = 0
        expected_transaction_list_b_first_page = transaction_list_b[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        retrieved_transaction_list_b_first_page = await transaction_repo.get_transaction_by_transfer_id(
            transfer_id=transfer_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_transaction_list_b_first_page) == len(
            expected_transaction_list_b_first_page
        ), "get transaction list by transfer id size should match with expected size"
        assert (
            retrieved_transaction_list_b_first_page
            == expected_transaction_list_b_first_page
        ), "retrieved transaction list by transfer id should match with expected list"
        # get the second page for transfer b
        offset = len(expected_transaction_list_b_first_page)
        expected_transaction_list_b_sec_page = transaction_list_b[
            TEST_DEFAULT_PAGE_SIZE:
        ]
        retrieved_transaction_list_b_sec_page = await transaction_repo.get_transaction_by_transfer_id(
            transfer_id=transfer_b.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_transaction_list_b_sec_page) == len(
            expected_transaction_list_b_sec_page
        ), "get transaction list by transfer id size should match with expected size"
        assert (
            retrieved_transaction_list_b_sec_page
            == expected_transaction_list_b_sec_page
        ), "retrieved transaction list by transfer id should match with expected list"

    async def test_get_transaction_by_transfer_id_return_empty(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # filter by transfer_id = -999
        transaction_list_invalid_transfer_id = await transaction_repo.get_transaction_by_transfer_id(
            transfer_id=-999, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert transaction_list_invalid_transfer_id == [], (
            "filtering by invalid transfer ids should return an empty "
            "transaction list"
        )

        # filter by a larger offset which is larger than the total amount for transfer_id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        count = 1
        await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer.id,
            count=count,
        )
        retrieved_transaction_list = await transaction_repo.get_transaction_by_transfer_id(
            transfer_id=transfer.id, offset=count + 1, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert retrieved_transaction_list == [], (
            "filtering by a larger offset than the total count should return an "
            "empty transaction list"
        )

    async def test_get_transaction_by_transfer_id_without_limit(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        count = 13
        transaction_list = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer.id,
            count=count,
        )

        # get total transactions for transfer
        retrieved_transaction_list = await transaction_repo.get_transaction_by_transfer_id_without_limit(
            transfer_id=transfer.id
        )
        assert len(retrieved_transaction_list) == len(
            transaction_list
        ), "get transaction list by transfer id size should match with expected size"
        assert (
            retrieved_transaction_list == transaction_list
        ), "retrieved transaction list by transfer id should match with expected list"

    async def test_get_transaction_by_payout_id(
        self,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        payout_a = await prepare_and_insert_payout(payout_repo=payout_repo)
        payout_b = await prepare_and_insert_payout(payout_repo=payout_repo)
        count_a = 4
        count_b = 13
        transaction_list_a = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            payout_id=payout_a.id,
            count=count_a,
        )
        transaction_list_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            payout_id=payout_b.id,
            count=count_b,
        )

        # get the first page for payout a
        offset = 0
        retrieved_transaction_list_a = await transaction_repo.get_transaction_by_payout_id(
            payout_id=payout_a.id, offset=offset, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_transaction_list_a) == len(
            transaction_list_a
        ), "get transaction list by payout id size should match with expected size"
        assert (
            retrieved_transaction_list_a == transaction_list_a
        ), "retrieved transaction list by payout id should match with expected list"

        # get limit transactions fewer than one page for payout b
        offset = 0
        limit = TEST_DEFAULT_PAGE_SIZE - 5
        expected_transaction_list_b_limit = transaction_list_b[:limit]
        retrieved_transaction_list_b_limit = await transaction_repo.get_transaction_by_payout_id(
            payout_id=payout_b.id, offset=offset, limit=limit
        )
        assert len(retrieved_transaction_list_b_limit) == len(
            expected_transaction_list_b_limit
        ), "get transaction list by payout id size should match with expected size"
        assert (
            retrieved_transaction_list_b_limit == expected_transaction_list_b_limit
        ), "retrieved transaction list by payout id should match with expected list"
        # get the second page for transfer b with limit
        offset = len(expected_transaction_list_b_limit)
        expected_transaction_list_b_sec_page = transaction_list_b[
            offset : offset + limit
        ]
        retrieved_transaction_list_b_sec_page = await transaction_repo.get_transaction_by_payout_id(
            payout_id=payout_b.id, offset=offset, limit=limit
        )
        assert len(retrieved_transaction_list_b_sec_page) == len(
            expected_transaction_list_b_sec_page
        ), "get transaction list by payout id size should match with expected size"
        assert (
            retrieved_transaction_list_b_sec_page
            == expected_transaction_list_b_sec_page
        ), "retrieved transaction list by payout id should match with expected list"

    async def test_get_transaction_by_payout_id_return_empty(
        self,
        transaction_repo: TransactionRepository,
        payout_repo: PayoutRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # filter by payout_id = -999
        transaction_list_invalid_payout_id = await transaction_repo.get_transaction_by_payout_id(
            payout_id=-999, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert transaction_list_invalid_payout_id == [], (
            "filtering by invalid payout id should return an empty " "transaction list"
        )

    async def test_get_transaction_by_payout_account_id(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # 1. prepare test data by inserting 30 transactions for the same payout account
        count = 30
        transaction_list = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            count=count,
        )
        expected_transaction_list_first_page_without_time_range = transaction_list[
            :TEST_DEFAULT_PAGE_SIZE
        ]

        # 2. get the first page for payout account id without time range
        offset = 0
        retrieved_transaction_list_first_page = await transaction_repo.get_transaction_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=offset,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert len(retrieved_transaction_list_first_page) == len(
            expected_transaction_list_first_page_without_time_range
        ), "get transaction list by payout id size should match with expected size"
        assert (
            retrieved_transaction_list_first_page
            == expected_transaction_list_first_page_without_time_range
        ), "retrieved transaction list by payout id should match with expected list"

        # 3. get second page of transactions with time_range
        expected_count = 8
        expected_transaction_list_first_page_with_time_range = transaction_list[
            TEST_DEFAULT_PAGE_SIZE : TEST_DEFAULT_PAGE_SIZE + expected_count
        ]
        end_time = expected_transaction_list_first_page_with_time_range[0].created_at
        start_time = expected_transaction_list_first_page_with_time_range[
            expected_count - 1
        ].created_at
        retrieved_transaction_list_first_page_with_time_range = await transaction_repo.get_transaction_by_payout_account_id(
            payout_account_id=payout_account_id,
            start_time=start_time,
            end_time=end_time,
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert len(retrieved_transaction_list_first_page_with_time_range) == len(
            expected_transaction_list_first_page_with_time_range
        ), "get transaction list by payout id size should match with expected size"
        assert (
            retrieved_transaction_list_first_page_with_time_range
            == expected_transaction_list_first_page_with_time_range
        ), "retrieved transaction list by payout id should match with expected list"

        # 4. get third page of transaction list with start_time only
        expected_transaction_list_first_page_with_start_time = transaction_list[
            : TEST_DEFAULT_PAGE_SIZE - 15
        ]
        expected_count = len(expected_transaction_list_first_page_with_start_time)
        start_time = expected_transaction_list_first_page_with_start_time[
            expected_count - 1
        ].created_at
        retrieved_transaction_list_first_page_with_start_time = await transaction_repo.get_transaction_by_payout_account_id(
            payout_account_id=payout_account_id,
            start_time=start_time,
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
        )
        assert (
            len(retrieved_transaction_list_first_page_with_start_time)
            == TEST_DEFAULT_PAGE_SIZE
        ), "get transaction list by payout id size should match with expected size"
        expected_transaction_list_first_page_with_start_time_first_page = expected_transaction_list_first_page_with_start_time[
            :TEST_DEFAULT_PAGE_SIZE
        ]
        assert (
            retrieved_transaction_list_first_page_with_start_time
            == expected_transaction_list_first_page_with_start_time_first_page
        ), "retrieved transaction list by payout id should match with expected list"

    async def test_get_transaction_by_payout_account_id_return_empty(
        self,
        transaction_repo: TransactionRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # filter by invalid payout account id
        retrieved_transaction_invalid_payout_account_id = await transaction_repo.get_transaction_by_payout_account_id(
            payout_account_id=-1, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert retrieved_transaction_invalid_payout_account_id == [], (
            "filtering by invalid payout account id should "
            "return an empty transaction list"
        )

    async def test_get_unpaid_transaction_by_payout_account_id(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # 1. prepare test data by adding 6 transactions for the same payout account
        count = 6
        transaction_list_unpaid = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            count=count,
        )
        # 2. insert another 6 paid transaction for the same payout account
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_paid_transaction_list_for_transfer(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer.id,
            count=count,
        )
        # 3. fetch unpaid transactions for the same payout account should return up to 10 transactions
        retrieved_unpaid_transaction_list = await transaction_repo.get_unpaid_transaction_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_unpaid_transaction_list) == len(
            transaction_list_unpaid
        ), "get unpaid transaction list by payout id size should match with expected size"
        assert (
            retrieved_unpaid_transaction_list == transaction_list_unpaid
        ), "retrieved unpaid transaction list by payout id should match with expected list"

        # 4. insert another unpaid transaction with state is ACTIVE
        data = TransactionCreateDBEntity(
            amount=1000,
            amount_paid=800,
            payment_account_id=payout_account_id,
            currency="USD",
            state=TransactionState.ACTIVE.value,
        )
        unpaid_transaction = await transaction_repo.create_transaction(data)

        # 5. get unpaid transaction list again should only return the first page of the transactions
        transaction_list_unpaid.insert(0, unpaid_transaction)
        retrieved_unpaid_transaction_list = await transaction_repo.get_unpaid_transaction_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_unpaid_transaction_list) == len(
            transaction_list_unpaid
        ), "get unpaid transaction list by payout id size should match with expected size"
        assert (
            retrieved_unpaid_transaction_list == transaction_list_unpaid
        ), "retrieved unpaid transaction list by payout id should match with expected list"

        # 6. list unpaid by start_time; start_time is the created_at of the 5th transaction
        index = 5
        start_time = transaction_list_unpaid[index].created_at
        expected_transaction_list_with_start_time = transaction_list_unpaid[: index + 1]
        retrieved_unpaid_transaction_list_with_start_time = await transaction_repo.get_unpaid_transaction_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
            start_time=start_time,
        )
        assert len(retrieved_unpaid_transaction_list_with_start_time) == len(
            expected_transaction_list_with_start_time
        ), "list unpaid transaction by start_time should return 6"
        assert (
            retrieved_unpaid_transaction_list_with_start_time
            == expected_transaction_list_with_start_time
        ), "list unpaid transaction by start_time should match with expected"

        # 7. list unpaid by start_time and end_time
        # start_time is the created_at of the 5th transaction
        # end_time is the created_at of the 8th transaction
        start_at_index = 5
        end_at_index = 3
        start_time = transaction_list_unpaid[start_at_index].created_at
        end_time = transaction_list_unpaid[end_at_index].created_at
        expected_transaction_list_with_time_range = transaction_list_unpaid[
            end_at_index : start_at_index + 1
        ]
        retrieved_unpaid_transaction_list_with_time_range = await transaction_repo.get_unpaid_transaction_by_payout_account_id(
            payout_account_id=payout_account_id,
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
            start_time=start_time,
            end_time=end_time,
        )
        assert len(retrieved_unpaid_transaction_list_with_time_range) == len(
            expected_transaction_list_with_time_range
        ), "list unpaid transaction by time_range should match with expected"
        assert (
            retrieved_unpaid_transaction_list_with_time_range
            == expected_transaction_list_with_time_range
        ), "list unpaid transaction by start_time should match with expected"

    async def test_get_unpaid_transaction_by_payout_account_id_return_empty(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_paid_transaction_list_for_transfer(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer.id,
            count=2,
        )
        retrieved_transaction_list = await transaction_repo.get_unpaid_transaction_by_payout_account_id(
            payout_account_id=payout_account_id, offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert retrieved_transaction_list == [], (
            "filtering unpaid transaction list should return an empty "
            "transaction when there's paid transaction only"
        )

    async def test_get_unpaid_transaction(
        self,
        transaction_repo: TransactionRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        payout_account_id: types.PayoutAccountId,
    ):
        # 1. prepare test data by adding 6 transactions for the payout account
        count = 6
        transaction_list_unpaid = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            count=count,
        )
        # 2. insert another 6 paid transaction for the same payout account
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_paid_transaction_list_for_transfer(
            transaction_repo=transaction_repo,
            payout_account_id=payout_account_id,
            transfer_id=transfer.id,
            count=count,
        )
        # 3. insert another 6 unpaid transactions for another payout account
        payment_account = await prepare_and_insert_payment_account(payment_account_repo)
        transaction_list_unpaid_b = await prepare_and_insert_transaction_list_for_same_account(
            transaction_repo=transaction_repo,
            payout_account_id=payment_account.id,
            count=count,
        )

        # 4. fetch unpaid transactions without time_range should return up to 10 transactions
        expected_first_page_transaction_list = (
            transaction_list_unpaid_b
            + transaction_list_unpaid[: TEST_DEFAULT_PAGE_SIZE - count]
        )
        retrieved_unpaid_transaction_list_first_page = await transaction_repo.get_unpaid_transaction(
            offset=0, limit=TEST_DEFAULT_PAGE_SIZE
        )
        assert len(retrieved_unpaid_transaction_list_first_page) == len(
            expected_first_page_transaction_list
        ), "get unpaid transaction list size should match with expected size"
        assert (
            retrieved_unpaid_transaction_list_first_page
            == expected_first_page_transaction_list
        ), "retrieved unpaid transaction list should match with expected list"

        # 5. list unpaid by start_time; start_time is the created_at of the 5th transaction
        total_unpaid_transaction_list = (
            transaction_list_unpaid_b + transaction_list_unpaid
        )
        index = 5
        start_time = total_unpaid_transaction_list[index].created_at
        expected_transaction_list_with_start_time = total_unpaid_transaction_list[
            : index + 1
        ]
        retrieved_unpaid_transaction_list_with_start_time = await transaction_repo.get_unpaid_transaction(
            offset=0, limit=TEST_DEFAULT_PAGE_SIZE, start_time=start_time
        )
        assert len(retrieved_unpaid_transaction_list_with_start_time) == len(
            expected_transaction_list_with_start_time
        ), "list unpaid transaction by start_time should return 6"
        assert (
            retrieved_unpaid_transaction_list_with_start_time
            == expected_transaction_list_with_start_time
        ), "list unpaid transaction by start_time should match with expected"

        # 6. list unpaid by start_time and end_time
        # start_time is the created_at of the 5th transaction
        # end_time is the created_at of the 8th transaction
        start_at_index = 5
        end_at_index = 3
        start_time = total_unpaid_transaction_list[start_at_index].created_at
        end_time = total_unpaid_transaction_list[end_at_index].created_at
        expected_transaction_list_with_time_range = total_unpaid_transaction_list[
            end_at_index : start_at_index + 1
        ]
        retrieved_unpaid_transaction_list_with_time_range = await transaction_repo.get_unpaid_transaction(
            offset=0,
            limit=TEST_DEFAULT_PAGE_SIZE,
            start_time=start_time,
            end_time=end_time,
        )
        assert len(retrieved_unpaid_transaction_list_with_time_range) == len(
            expected_transaction_list_with_time_range
        ), "list unpaid transaction by time_range should match with expected"
        assert (
            retrieved_unpaid_transaction_list_with_time_range
            == expected_transaction_list_with_time_range
        ), "list unpaid transaction by start_time should match with expected"

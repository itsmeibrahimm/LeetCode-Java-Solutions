from secrets import token_hex

import pytest
from pytest_mock import MockFixture
from sqlalchemy import column, table

from app.commons.database.infra import DB
from app.commons.database.query import paged_query

pytestmark = [pytest.mark.asyncio]


@pytest.fixture
def test_table_name():
    return token_hex(16)


@pytest.fixture
async def create_test_table(payin_maindb: DB, test_table_name: str):
    print(f"Creating table {test_table_name}")
    await payin_maindb.master().execute(f'create table "{test_table_name}"(id serial)')
    yield
    print(f"Dropping table {test_table_name}")
    await payin_maindb.master().execute(f'drop table "{test_table_name}"')


async def test_paging_query(
    payin_maindb: DB, create_test_table, test_table_name: str, mocker: MockFixture
):
    spy_fetch_all = mocker.spy(payin_maindb.master(), "fetch_all")

    test_table = table(test_table_name, column("id"))
    for i in range(5):
        query = test_table.insert().values(id=i)
        await payin_maindb.master().execute(query)

    query = test_table.select(test_table)
    desc_ids = [
        result["id"]
        async for result in paged_query(
            payin_maindb.master(),
            query,
            pk_attr=column("id"),
            batch_size=2,
            desc_order=True,
        )
    ]

    assert desc_ids == [4, 3, 2, 1, 0]
    # 5 elements, batch_size of 2
    assert spy_fetch_all.call_count == 3  # type: ignore

    asc_ids = [
        result["id"]
        async for result in paged_query(
            payin_maindb.master(), query, pk_attr=column("id"), batch_size=2
        )
    ]
    assert asc_ids == [0, 1, 2, 3, 4]
    # 5 elements, batch_size of 2
    assert spy_fetch_all.call_count == 6  # type: ignore


async def test_cross_database_connection_acquisition(payout_maindb: DB):
    master = payout_maindb.master().connection()
    replica = payout_maindb.replica().connection()

    async def connection_task():
        master = payout_maindb.master().connection()
        replica = payout_maindb.replica().connection()
        return id(master), id(replica)

    assert id(master) != id(replica), "master and replicas have different connections"
    task_master_id, task_replica_id = await connection_task()
    assert task_master_id == id(master), "master connection is inherited by task"
    assert task_replica_id == id(replica), "replica connection is inherited by task"


async def test_cross_database_transaction(
    payout_maindb: DB, payin_maindb: DB, create_test_table, test_table_name: str
):
    test_table = table(test_table_name, column("id"))

    import contextlib

    with contextlib.suppress(RuntimeError):
        # NOTE: we should avoid this in real production code
        async with payout_maindb.master().transaction():
            async with payin_maindb.master().transaction() as transaction:
                insert = test_table.insert().values(id=777)
                await transaction.connection().execute(insert)
        # outer transaction on payout is rolled back
        raise RuntimeError()
    query = test_table.select().where(test_table.c.id == 777)
    assert (
        await payin_maindb.master().fetch_value(query) == 777
    ), "inner transaction on a different db is not affected"

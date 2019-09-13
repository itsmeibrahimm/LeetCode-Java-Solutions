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
    ids = [
        result["id"]
        async for result in paged_query(
            payin_maindb.master(), query, pk_attr=column("id"), batch_size=2
        )
    ]
    assert ids == list(range(5))
    # 5 elements, batch_size of 2
    assert spy_fetch_all.call_count == 3  # type: ignore

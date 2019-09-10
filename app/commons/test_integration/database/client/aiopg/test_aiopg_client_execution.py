from collections import Sequence
from datetime import datetime

import pytest

from app.commons.config.app_config import AppConfig
from app.commons.database.client.aiopg import AioEngine, AioTransaction
from app.payout.repository.maindb.model import payment_accounts

pytestmark = [pytest.mark.asyncio]


@pytest.fixture
async def payout_maindb_aio_engine(app_config: AppConfig):
    assert app_config.PAYOUT_MAINDB_MASTER_URL.value
    engine = AioEngine(
        dsn=app_config.PAYOUT_MAINDB_MASTER_URL.value,
        minsize=2,
        maxsize=2,
        debug=True,
        default_stmt_timeout_sec=1.5,
    )
    await engine.connect()
    async with engine:
        yield engine
    assert engine.closed(), "engine was not closed properly"


async def test_statement_timeout(payout_maindb_aio_engine: AioEngine):
    assert (
        await payout_maindb_aio_engine.fetch_value("SHOW statement_timeout") == "1500ms"
    ), "statement timeout is set (in ms)"


async def test_create_and_fetch_one_fetch_many_fetch_value(
    payout_maindb_aio_engine: AioEngine
):
    entity = "dasher" + str(datetime.utcnow())
    account_1_stmt = (
        payment_accounts.table.insert()
        .values(
            {
                payment_accounts.entity: entity,
                payment_accounts.account_type: "sma",
                payment_accounts.statement_descriptor: "something",
            }
        )
        .returning(*payment_accounts.table.columns)
    )
    account_2_stmt = (
        payment_accounts.table.insert()
        .values(
            {
                payment_accounts.entity: entity,
                payment_accounts.account_type: "ams",
                payment_accounts.statement_descriptor: "somthing else",
            }
        )
        .returning(*payment_accounts.table.columns)
    )

    account_1 = await payout_maindb_aio_engine.fetch_one(stmt=account_1_stmt)
    account_2 = await payout_maindb_aio_engine.fetch_one(stmt=account_2_stmt)
    assert account_1
    assert account_2
    assert account_1["id"]
    assert account_2["id"]
    assert account_1["entity"] == account_2["entity"] == entity

    stmt = payment_accounts.table.select().where(payment_accounts.entity == entity)

    one_result = await payout_maindb_aio_engine.fetch_one(stmt)
    assert one_result
    assert one_result["id"]
    assert one_result["entity"] == entity

    all_result = await payout_maindb_aio_engine.fetch_all(stmt)
    assert all_result
    assert len(all_result) == 2
    result_with_same_entity = [row for row in all_result if row["entity"] == entity]
    assert len(result_with_same_entity) == len(all_result)

    count_stmt = f"select count(*) from payment_account where entity='{entity}'"
    value_result = await payout_maindb_aio_engine.fetch_value(count_stmt)
    assert value_result == 2


async def test_fetch_one_fetch_many_fetch_value_but_nothing(
    payout_maindb_aio_engine: AioEngine
):
    nothing = str(datetime.utcnow())

    nothing_stmt = payment_accounts.table.select().where(
        payment_accounts.statement_descriptor == nothing
    )
    nothing_one = await payout_maindb_aio_engine.fetch_one(stmt=nothing_stmt)
    assert nothing_one is None

    nothing_all = await payout_maindb_aio_engine.fetch_all(stmt=nothing_stmt)
    assert not nothing_all
    assert isinstance(nothing_all, Sequence)

    nothing_value = await payout_maindb_aio_engine.fetch_value(stmt=nothing_stmt)
    assert nothing_value is None


async def test_transaction_intentionally_rollback(payout_maindb_aio_engine: AioEngine):
    async with payout_maindb_aio_engine.transaction() as tx:  # type: AioTransaction
        account_stmt = (
            payment_accounts.table.insert()
            .values(
                {
                    payment_accounts.account_type: "sma",
                    payment_accounts.statement_descriptor: "something"
                    + str(datetime.utcnow()),
                }
            )
            .returning(*payment_accounts.table.columns)
        )
        account = await tx.connection().fetch_one(account_stmt)
        assert account
        assert account["id"]
        id = account["id"]

        retrival_stmt = payment_accounts.table.select().where(payment_accounts.id == id)

        retrieved = await tx.connection().fetch_one(retrival_stmt)
        assert retrieved
        assert retrieved["id"] == id
        await tx.rollback()
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone


async def test_transaction_error_rollback(payout_maindb_aio_engine: AioEngine):

    with pytest.raises(Exception):
        async with payout_maindb_aio_engine.transaction() as tx:  # type: AioTransaction
            retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx
            )
            raise Exception("Error rolling back now!!!")

    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone


async def test_multiple_level_intentionally_transaction_rollback(
    payout_maindb_aio_engine: AioEngine
):

    # [should be rollback]  execute with outer tx and rollback outer tx at outer level
    async with payout_maindb_aio_engine.transaction() as tx11:  # type: AioTransaction
        async with payout_maindb_aio_engine.transaction() as tx12:
            retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx11
            )
        await tx11.rollback()
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx11.active()
    assert not tx12.active()

    # [should be rollback]  execute with outer tx and rollback outer tx at inner level
    async with payout_maindb_aio_engine.transaction() as tx21:  # type: AioTransaction
        async with payout_maindb_aio_engine.transaction() as tx22:
            retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx21
            )
            await tx21.rollback()
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx21.active()
    assert not tx22.active()

    # [should be rollback] execute with inner tx and rollback inner tx at inner level
    async with payout_maindb_aio_engine.transaction() as tx31:  # type: AioTransaction
        async with payout_maindb_aio_engine.transaction() as tx32:
            retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx32
            )
            await tx32.rollback()
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx31.active()
    assert not tx32.active()

    # [should fail at rollback] execute with inner tx and rollback inner tx at inner level

    async with payout_maindb_aio_engine.transaction() as tx41:  # type: AioTransaction
        async with payout_maindb_aio_engine.transaction() as tx42:
            retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx42
            )
        await tx42.rollback()
    account_should_not_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert account_should_not_gone
    assert account_should_not_gone["id"] == id
    assert not tx41.active()
    assert not tx42.active()


async def test_multiple_level_error_transaction_rollback(
    payout_maindb_aio_engine: AioEngine
):
    # [should be rollback]  execute with outer tx and exception at outer level
    with pytest.raises(Exception):
        async with payout_maindb_aio_engine.transaction() as tx11:  # type: AioTransaction
            async with payout_maindb_aio_engine.transaction() as tx12:
                retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                    tx11
                )
            raise Exception("should rollback!")
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx11.active()
    assert not tx12.active()

    # [should be rollback]  execute with outer tx and exception at inner level
    with pytest.raises(Exception):
        async with payout_maindb_aio_engine.transaction() as tx21:  # type: AioTransaction
            async with payout_maindb_aio_engine.transaction() as tx22:
                retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                    tx21
                )
                raise Exception("should rollback!")
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx21.active()
    assert not tx22.active()

    # [should be rollback] execute with inner tx and exception at inner level
    with pytest.raises(Exception):
        async with payout_maindb_aio_engine.transaction() as tx31:  # type: AioTransaction
            async with payout_maindb_aio_engine.transaction() as tx32:
                retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                    tx32
                )
                raise Exception("should rollback!")
    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert not account_gone
    assert not tx31.active()
    assert not tx32.active()

    # [should fail at rollback] execute with inner tx and rollback inner tx at inner level
    with pytest.raises(Exception):
        async with payout_maindb_aio_engine.transaction() as tx41:  # type: AioTransaction
            async with payout_maindb_aio_engine.transaction() as tx42:
                retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                    tx42
                )
            raise Exception("should rollback!")
    account_should_not_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert account_should_not_gone
    assert account_should_not_gone["id"] == id
    assert not tx41.active()
    assert not tx42.active()


async def test_transaction_commit(payout_maindb_aio_engine: AioEngine):
    async with payout_maindb_aio_engine.transaction() as tx:  # type: AioTransaction
        retrival_stmt, id = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
            tx
        )
    account_stay = await payout_maindb_aio_engine.fetch_one(retrival_stmt)
    assert account_stay
    assert account_stay["id"] == id


async def test_transaction_commit_with_partial_rollback(
    payout_maindb_aio_engine: AioEngine
):
    async with payout_maindb_aio_engine.transaction() as tx1:  # type: AioTransaction
        retrival_stmt_1, id_1 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
            tx1
        )
        async with payout_maindb_aio_engine.transaction() as tx2:
            retrival_stmt_2, id_2 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx2
            )
            await tx2.rollback()
    account_stay = await payout_maindb_aio_engine.fetch_one(retrival_stmt_1)
    assert account_stay
    assert account_stay["id"] == id_1

    account_gone = await payout_maindb_aio_engine.fetch_one(retrival_stmt_2)
    assert not account_gone
    assert not tx1.active()
    assert not tx2.active()


async def test_only_outer_most_commit_is_effective_within_same_connection(
    payout_maindb_aio_engine: AioEngine
):

    #  Inner committed but outer rollback, so all should be rolled back
    async with payout_maindb_aio_engine.transaction() as tx11:  # type: AioTransaction
        retrival_stmt_1, id_1 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
            tx11
        )
        async with tx11.connection().transaction() as tx12:  # type: AioTransaction
            retrival_stmt_2, id_2 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx12
            )
            await tx12.commit()
        await tx11.rollback()
    account_gone_1 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_1)
    assert not account_gone_1

    account_gone_2 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_2)
    assert not account_gone_2
    assert not tx11.active()
    assert not tx12.active()

    #  Inner rollback, so all should be rolled back
    async with payout_maindb_aio_engine.transaction() as tx21:  # type: AioTransaction
        retrival_stmt_1, id_1 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
            tx21
        )
        async with tx21.connection().transaction() as tx22:  # type: AioTransaction
            retrival_stmt_2, id_2 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx22
            )
            await tx21.rollback()
    account_gone_1 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_1)
    assert not account_gone_1

    account_gone_2 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_2)
    assert not account_gone_2
    assert not tx21.active()
    assert not tx22.active()

    #  no rollback everything works fine
    async with payout_maindb_aio_engine.transaction() as tx31:  # type: AioTransaction
        retrival_stmt_1, id_1 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
            tx31
        )
        async with tx31.connection().transaction() as tx32:  # type: AioTransaction
            retrival_stmt_2, id_2 = await _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
                tx32
            )
    account_stay_1 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_1)
    assert account_stay_1
    assert account_stay_1["id"] == id_1

    account_stay_2 = await payout_maindb_aio_engine.fetch_one(retrival_stmt_2)
    assert account_stay_2
    assert account_stay_2["id"] == id_2
    assert not tx31.active()
    assert not tx32.active()


async def _create_account_validate_within_transaction_then_return_retrieval_stmt_and_id(
    tx: AioTransaction
):
    #  Create account within an active transaction, validate it within transaction
    #  and return its id without closing/committing/rollback transaction
    assert tx.active(), "tx is not active!"
    account_stmt = (
        payment_accounts.table.insert()
        .values(
            {
                payment_accounts.account_type: "sma",
                payment_accounts.statement_descriptor: "something"
                + str(datetime.utcnow()),
            }
        )
        .returning(*payment_accounts.table.columns)
    )
    account = await tx.connection().fetch_one(account_stmt)
    assert account
    assert account["id"]
    id = account["id"]

    retrival_stmt = payment_accounts.table.select().where(payment_accounts.id == id)

    retrieved = await tx.connection().fetch_one(retrival_stmt)
    assert retrieved
    assert retrieved["id"] == id
    return (retrival_stmt, id)

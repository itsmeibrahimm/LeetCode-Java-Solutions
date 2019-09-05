import pytest
from typing import List
from app.commons.database.infra import DB
from app.commons.utils.testing import Stat


class MyRepository:
    def __init__(self, db: DB):
        self.db = db

    async def insert_name(self):
        return await self.db.master().fetch_value("SELECT 1")

    async def with_transaction(self):
        async with self.db.master().transaction() as transaction:
            connection = transaction.connection()
            return await self.insert_conn(connection)

    async def insert_conn(self, connection):
        return await connection.fetch_value("SELECT 2")


class TestTiming:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, service_statsd_client):
        # ensure that we mock the statsd service client
        ...

    async def test_stats_query(self, payin_maindb: DB, get_mock_statsd_events):
        repository = MyRepository(payin_maindb)

        assert await repository.insert_name() == 1

        events: List[Stat] = get_mock_statsd_events()
        event_names = [event.stat_name for event in events]

        assert (
            "dd.pay.payment-service.io.payin_maindb.query.insert_name.latency"
            in event_names
        )

    async def test_stats_transaction(self, payin_maindb: DB, get_mock_statsd_events):
        repository = MyRepository(payin_maindb)

        assert await repository.with_transaction() == 2

        events: List[Stat] = get_mock_statsd_events()
        event_names = [event.stat_name for event in events]

        assert (
            "dd.pay.payment-service.io.payin_maindb.transaction.with_transaction.latency"
            in event_names
        )
        assert (
            "dd.pay.payment-service.io.payin_maindb.query.insert_conn.latency"
            in event_names
        )

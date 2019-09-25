import pytest
import sys
from unittest import mock
from typing import List
from app.commons import tracing, timing
from app.commons.utils.testing import Stat
from app.commons.timing.database import _discover_caller


class TestDiscover:
    def caller(self, additional_ignores=None):
        return _discover_caller(additional_ignores=additional_ignores)

    def test_find(self):
        f, name = self.caller()
        assert name == __name__, "returns the name of the caller"

    def test_find_exclude(self):
        f, name = self.caller(["app.commons.test_unit"])
        assert name != __name__, "exclude unit tests"


class Transaction:
    def __init__(self, database):
        self.database = database
        self.manager = timing.database.TransactionTimingManager(
            message="transaction complete"
        )

    async def __aenter__(self):
        f = sys._getframe()
        f = f.f_back
        # hack to ignore this function when determining caller
        with mock.patch(
            "app.commons.timing.database._discover_caller",
            return_value=(f, f.f_globals.get("__name__")),
        ):
            self.manager.start(obj=self.database, func=None, args=[], kwargs={})

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.manager.rollback(obj=self.database)
        else:
            self.manager.commit(obj=self.database)


class Database(timing.database.Database, timing.database.TrackedTransaction):
    database_name = "somedb"
    instance_name = "master"

    tracker = None
    stack = None

    def transaction(self):
        return Transaction(self)

    @timing.database.track_execute
    async def query(self, *args, **kwargs):
        ...


# ensure stats have app name
@tracing.track_breadcrumb(application_name="my-app")
class Caller:
    db = Database()

    async def do_something(self):
        async with self.db.transaction():
            ...
            await self.insert_into_table()
            await self.update_table()
            return 1

    async def insert_into_table(self):
        await self.db.query()

    async def update_table(self):
        await self.db.query()

    async def insert_without_transaction(self):
        await self.db.query()


class TestDatabaseTimingTracker:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, service_statsd_client):
        # ensure that we mock the statsd service client
        ...

    async def test_transaction(self, get_mock_statsd_events):

        caller = Caller()
        assert await caller.do_something() == 1

        events: List[Stat] = get_mock_statsd_events()
        stat_names = {
            (event.stat_name, event.tags["query_name"]): event for event in events
        }

        # query timing
        insert_name = ("dd.pay.payment-service.io.db.latency", "insert_into_table")
        assert insert_name in stat_names, "insert query exists"
        insert_query = stat_names[insert_name]
        assert insert_query.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            "transaction_name": "do_something",
            "query_name": "insert_into_table",
            "request_status": "success",
        }

        update_name = ("dd.pay.payment-service.io.db.latency", "update_table")
        assert update_name in stat_names, "update query exists"
        update_query = stat_names[update_name]
        assert update_query.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            "transaction_name": "do_something",
            "query_name": "update_table",
            "request_status": "success",
        }

        # transaction timing
        transaction_name = ("dd.pay.payment-service.io.db.latency", "do_something")
        assert transaction_name in stat_names, "transaction exists"
        transaction = stat_names[transaction_name]
        assert (
            "transaction_name" not in transaction.tags
        ), "transaction_name is only set on transactions if they are nested"
        assert transaction.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            # "transaction_name": "do_something",
            "query_type": "transaction",
            "query_name": "do_something",
            "request_status": "commit",
        }

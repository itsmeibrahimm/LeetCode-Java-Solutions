import contextlib
import pytest
import re
from collections import namedtuple
from unittest.mock import Mock
from app.commons import timing, stats
from app.commons.timing import _discover_caller

STATSD_METRIC_FORMAT = re.compile(
    r"^(?P<metric>[a-zA-Z0-9-_.]+)(?P<tags>[a-zA-Z0-9-_.~=]+)?:(?P<value>[0-9.]+)(|(?P<unit>\w+))"
)
StatsDMetric = namedtuple("StatsDMetric", ["metric", "value", "unit", "tags"])


def tags_from_raw_metric(raw_tags):
    raw_tags = raw_tags or ""

    tags = {}
    for key_value in raw_tags.split("~"):
        if not key_value:
            continue
        key_value = key_value.split("=", 2)
        if len(key_value) < 2:
            continue
        key, value = key_value
        tags[key] = value
    return tags


class TestDiscover:
    def caller(self, additional_ignores=None):
        return _discover_caller(additional_ignores=additional_ignores)

    def test_find(self):
        f, name = self.caller()
        assert (
            name == "app.commons.test_unit.test_timing"
        ), "returns the name of the caller"

    def test_find_exclude(self):
        f, name = self.caller(["app.commons.test_unit"])
        assert name != "app.commons.test_unit.test_timing", "exclude unit tests"


class TestDatabaseTimingTracker:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self):
        self.statsd_client = stats.init_statsd("dd.response", host="localhost")
        with stats.set_service_stats_client(self.statsd_client):
            yield

    async def test_transaction(self, mock_statsd_client: Mock):
        @contextlib.asynccontextmanager
        async def transaction_manager():
            yield "some transaction"

        class Database(timing.Database):
            database_name = "some db"
            instance_name = "master"

            @timing.track_transaction
            def transaction(self):
                return transaction_manager()

            @timing.track_query
            async def query(self, *args, **kwargs):
                ...

        class Caller:
            db = Database()

            async def do_something(self):
                async with self.db.transaction():
                    ...
                    await self.insert_into_table()
                    await self.update_table()

            async def insert_into_table(self):
                await self.db.query()

            async def update_table(self):
                await self.db.query()

            async def insert_without_transaction(self):
                await self.db.query()

        caller = Caller()
        await caller.do_something()
        # dd.response.io.some-db.query.enter_context.latency~cluster=master~transaction=no~transaction_name=:5.885283|ms

        stats = []
        for args, _ in mock_statsd_client.call_args_list:
            match = STATSD_METRIC_FORMAT.match(args[0])
            if not match:
                pytest.fail(f"invalid metric {args[0]}")
                return
            metric, value, unit = match.group("metric", "value", "unit")
            tags = tags_from_raw_metric(match.group("tags"))
            stats.append(StatsDMetric(metric, value, unit, tags))
        stat_names = [stat.metric for stat in stats]

        # query timing
        assert "dd.response.io.some-db.query.insert_into_table.latency" in stat_names
        assert "dd.response.io.some-db.query.update_table.latency" in stat_names

        # transaction timing
        assert "dd.response.io.some-db.transaction.do_something.latency" in stat_names

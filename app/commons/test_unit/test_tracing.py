import pytest
import asyncio
import time
from app.commons import tracing


class TestContextDecorator:
    def test_app(self):
        class SyncObject:
            @tracing.set_app_name("myapp")
            def with_app(self):
                return tracing.get_app_name()

        tester = SyncObject()

        assert tracing.get_app_name() == ""
        assert tester.with_app() == "myapp"
        assert tracing.get_app_name() == ""
        assert tracing.get_app_name("appdefault") == "appdefault"

    def test_processor(self):
        class SyncObject:
            @tracing.set_processor_name("myprocessor")
            def with_processor(self):
                return tracing.get_processor_name()

        tester = SyncObject()

        assert tracing.get_processor_name() == ""
        assert tester.with_processor() == "myprocessor"
        assert tracing.get_processor_name() == ""
        assert tracing.get_processor_name("procdefault") == "procdefault"

    def test_repository(self):
        class SyncObject:
            def with_repo(self):
                return tracing.get_repository_name()

            def __getattribute__(self, name):
                attr = super().__getattribute__(name)
                if callable(attr):
                    return tracing.set_repository_name("myrepo")(attr)
                return attr

        tester = SyncObject()

        assert tracing.get_repository_name() == ""
        assert tester.with_repo() == "myrepo"
        assert tracing.get_repository_name() == ""
        assert tracing.get_repository_name("repodefault") == "repodefault"

    @pytest.mark.asyncio
    async def test_async(self):
        class AsyncObject:
            @tracing.set_app_name("asyncapp")
            async def with_app(self):
                return tracing.get_app_name()

        tester = AsyncObject()

        assert tracing.get_app_name() == ""
        assert await tester.with_app() == "asyncapp"
        assert tracing.get_app_name("mydefault") == "mydefault"


class TestContextClassDecorator:
    @pytest.mark.asyncio
    async def test_decorated_class(self):
        @tracing.set_database_name("classdbname")
        class DecoratedClass:
            @tracing.trackable
            def sync_method(self):
                return tracing.get_database_name()

            @tracing.trackable
            async def async_method(self):
                return tracing.get_database_name()

            def sync_not_tracked(self):
                return tracing.get_database_name()

            async def async_not_tracked(self):
                return tracing.get_database_name()

        tester = DecoratedClass()

        assert tracing.is_trackable(tester.sync_method)
        assert tracing.is_trackable(tester.async_method)
        assert not tracing.is_trackable(tester.sync_not_tracked)
        assert not tracing.is_trackable(tester.async_not_tracked)

        assert tracing.get_database_name() == ""
        assert tracing.get_database_name("custom") == "custom"

        assert tester.sync_method() == "classdbname"
        assert tracing.get_database_name() == ""

        future = tester.async_method()
        assert tracing.get_database_name() == ""
        assert await future == "classdbname"
        assert tracing.get_database_name() == ""

        assert tester.sync_not_tracked() == ""
        assert await tester.async_not_tracked() == ""

    def test_trackable_class(self):
        @tracing.set_transaction_name("mytxn", only_trackable=False)
        class Trackable:
            def trackable(self):
                return tracing.get_transaction_name()

        tester = Trackable()

        assert tracing.is_trackable(tester.trackable)
        assert tester.trackable() == "mytxn"

    def test_decorated_instance(self):
        class Trackable:
            def trackable(self):
                return tracing.get_transaction_name()

        tester = Trackable()
        assert tester.trackable() == ""

        tester = tracing.set_transaction_name("inst")(Trackable())
        assert tester.trackable() == ""

        tester = tracing.set_transaction_name("inst", only_trackable=False)(Trackable())
        assert tester.trackable() == "inst"


@pytest.mark.skip("deprecated")
class TestContextContextManager:
    def test_sync(self):
        assert tracing.get_method_name() == ""

        with tracing.set_method_name("mymethod") as manager:
            assert tracing.get_method_name() == "mymethod"
            assert isinstance(manager, tracing.ContextVarTracker)

        assert tracing.get_method_name() == ""

    async def myasyncmethod(self):
        return tracing.get_method_name()

    @pytest.mark.asyncio
    async def test_async(self):
        assert tracing.get_method_name() == ""

        with tracing.set_method_name("asyncmethod"):
            assert tracing.get_method_name() == "asyncmethod"
            assert await self.myasyncmethod() == "asyncmethod"

        assert tracing.get_method_name() == ""
        assert await self.myasyncmethod() == ""


class TestTimer:
    def test_sync(self):
        with tracing.Timer() as timer:
            time.sleep(0.125)
        assert timer.delta >= 0.125
        assert timer.delta_ms >= 125

    @pytest.mark.asyncio
    async def test_async(self):
        with tracing.Timer() as timer:
            await asyncio.sleep(0.125)
        assert timer.delta >= 0.125
        assert timer.delta_ms >= 125

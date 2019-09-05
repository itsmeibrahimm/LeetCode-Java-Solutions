import pytest
import asyncio
import time
import pydantic
from collections import deque
from app.commons import tracing


class TestContextDecorator:
    def test_app(self):
        class SyncObject:
            @tracing.track_breadcrumb(application_name="myapp")
            def with_app(self):
                return tracing.get_application_name()

        tester = SyncObject()

        assert tracing.get_application_name() == ""
        assert tester.with_app() == "myapp"
        assert tracing.get_application_name() == ""
        assert tracing.get_application_name("appdefault") == "appdefault"

    def test_processor(self):
        class SyncObject:
            @tracing.track_breadcrumb(processor_name="myprocessor")
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
                    return tracing.track_breadcrumb(repository_name="myrepo")(attr)
                return attr

        tester = SyncObject()

        assert tracing.get_repository_name() == ""
        assert tester.with_repo() == "myrepo"
        assert tracing.get_repository_name() == ""
        assert tracing.get_repository_name("repodefault") == "repodefault"

    @pytest.mark.asyncio
    async def test_async(self):
        class AsyncObject:
            @tracing.track_breadcrumb(application_name="asyncapp")
            async def with_app(self):
                return tracing.get_application_name()

        tester = AsyncObject()

        assert tracing.get_application_name() == ""
        assert await tester.with_app() == "asyncapp"
        assert tracing.get_application_name("mydefault") == "mydefault"


class TestContextClassDecorator:
    @pytest.mark.asyncio
    async def test_decorated_class(self):
        @tracing.track_breadcrumb(database_name="tracked")
        class TrackEverything:
            @tracing.trackable
            def sync_method(self):
                return tracing.get_database_name()

            @tracing.trackable
            async def async_method(self):
                return tracing.get_database_name()

            def sync_not_trackable(self):
                return tracing.get_database_name()

            async def async_not_trackable(self):
                return tracing.get_database_name()

        tester = TrackEverything()
        assert tracing.is_trackable(tester.sync_method)
        assert tracing.is_trackable(tester.async_method)
        assert tracing.is_trackable(tester.sync_not_trackable)
        assert tracing.is_trackable(tester.async_not_trackable)

        assert tester.sync_method() == "tracked"
        assert await tester.async_method() == "tracked"
        assert tester.sync_not_trackable() == "tracked"
        assert await tester.async_not_trackable() == "tracked"

    @pytest.mark.asyncio
    async def test_decorated_class_only_trackable(self):
        @tracing.track_breadcrumb(database_name="classdbname", only_trackable=True)
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
        @tracing.track_breadcrumb(transaction_name="mytxn")
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

        tester = tracing.track_breadcrumb(transaction_name="inst", only_trackable=True)(
            Trackable()
        )
        assert tester.trackable() == ""

        tester = tracing.track_breadcrumb(transaction_name="inst")(Trackable())
        assert tester.trackable() == "inst"


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


class TestBreadcrumbs:
    def test_breadcrumb(self):
        breadcrumb = tracing.Breadcrumb()
        assert breadcrumb.dict(skip_defaults=True) == {}

        breadcrumb = tracing.Breadcrumb(application_name="my-app-v1")
        assert breadcrumb.dict(skip_defaults=True) == {"application_name": "my-app-v1"}

        with pytest.raises(pydantic.error_wrappers.ValidationError):
            tracing.Breadcrumb(not_valid=None)

    def test_breadcrumb_utils(self):
        a = tracing.Breadcrumb(application_name="my-app-v2")
        b = tracing.Breadcrumb(processor_name="myproc")
        merged = tracing._merge_breadcrumbs(a, b)
        assert merged == tracing.Breadcrumb(
            application_name="my-app-v2", processor_name="myproc"
        )
        assert merged.dict(skip_defaults=True) == dict(
            application_name="my-app-v2", processor_name="myproc"
        )

    def test_get_breadcrumbs(self):
        assert tracing.get_breadcrumbs() == deque([])
        assert tracing.get_current_breadcrumb() == tracing.Breadcrumb()

    def test_nested(self):
        assert tracing.get_current_breadcrumb() == tracing.Breadcrumb()

        with tracing.breadcrumb_as(tracing.Breadcrumb(application_name="nested")):
            assert tracing.get_current_breadcrumb() == tracing.Breadcrumb(
                application_name="nested"
            )
            assert len(tracing.get_breadcrumbs()) == 1

            with tracing.breadcrumb_as(tracing.Breadcrumb(processor_name="multiple")):
                assert tracing.get_current_breadcrumb() == tracing.Breadcrumb(
                    application_name="nested", processor_name="multiple"
                )
                assert len(tracing.get_breadcrumbs()) == 2

                with tracing.breadcrumb_as(
                    tracing.Breadcrumb(repository_name="levels")
                ):
                    assert tracing.get_current_breadcrumb() == tracing.Breadcrumb(
                        application_name="nested",
                        processor_name="multiple",
                        repository_name="levels",
                    )
                    assert tracing.get_current_breadcrumb().dict(
                        skip_defaults=True
                    ) == dict(
                        application_name="nested",
                        processor_name="multiple",
                        repository_name="levels",
                    )
                    assert tracing.get_breadcrumbs() == deque(
                        [
                            tracing.Breadcrumb(
                                application_name="nested",
                                processor_name="multiple",
                                repository_name="levels",
                            ),
                            tracing.Breadcrumb(
                                application_name="nested", processor_name="multiple"
                            ),
                            tracing.Breadcrumb(application_name="nested"),
                        ]
                    )
                    assert len(tracing.get_breadcrumbs()) == 3

                assert tracing.get_current_breadcrumb() == tracing.Breadcrumb(
                    application_name="nested", processor_name="multiple"
                )
            assert tracing.get_current_breadcrumb() == tracing.Breadcrumb(
                application_name="nested"
            )

        assert tracing.get_current_breadcrumb() == tracing.Breadcrumb()

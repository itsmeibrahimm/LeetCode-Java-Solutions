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
        with tracing.BaseTimer() as timer:
            time.sleep(0.125)
        assert timer.delta >= 0.125
        assert timer.delta_ms >= 125

    @pytest.mark.asyncio
    async def test_async(self):
        with tracing.BaseTimer() as timer:
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

    def test_validate_from_kwargs(self):
        tracing.BreadcrumbManager.validate_from_kwargs({})
        tracing.BreadcrumbManager.validate_from_kwargs({"valid": "country"})

        with pytest.raises(ValueError, match=r"arg => field_does_not_exist"):
            tracing.BreadcrumbManager.validate_from_kwargs(
                {"arg": "field_does_not_exist"}
            )

    def test_from_kwargs(self):
        assert (
            tracing.BreadcrumbManager.breadcrumb_from_kwargs({}, {})
            == tracing.Breadcrumb()
        ), "empty"

        assert (
            tracing.BreadcrumbManager.breadcrumb_from_kwargs(
                {"non-existent": "application_name"}, {}
            )
            == tracing.Breadcrumb()
        ), "non-existent field in kwargs"

        assert tracing.BreadcrumbManager.breadcrumb_from_kwargs(
            {"appname": "application_name"}, {"appname": "blah"}
        ) == tracing.Breadcrumb(
            application_name="blah"
        ), "successfully mapped breadcrumb"

        assert tracing.BreadcrumbManager.breadcrumb_from_kwargs(
            {"appname": "application_name", "reponame": "repository_name"},
            {"appname": "valid", "reponame": dict(invalid="value")},
        ) == tracing.Breadcrumb(
            application_name="valid"
        ), "field with invalid type `repository_name` is silently ignored"

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

    def test_tracking(self):
        @tracing.track_breadcrumb(application_name="nested", only_trackable=True)
        class TrackedClass:
            @tracing.track_breadcrumb(application_name="app")
            def application_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(processor_name="proc")
            def processor_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(repository_name="repo")
            def repository_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(database_name="db")
            def database_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(instance_name="inst")
            def instance_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(provider_name="prov")
            def provider_name(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(country="MX")
            def country(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(resource="res")
            def resource(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(action="yes")
            def action(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(status_code="200")
            def status_code(self):
                return tracing.get_current_breadcrumb()

            def not_tracked(self):
                return tracing.get_current_breadcrumb()

            @tracing.track_breadcrumb(
                from_kwargs={
                    "act": "action",
                    "opt_resource": "resource",
                    "opt_app": "application_name",
                }
            )
            def override_app(self, *, act, opt_resource=None, opt_app=None):
                return tracing.get_current_breadcrumb()

        obj = TrackedClass()

        assert obj.application_name() == tracing.Breadcrumb(
            application_name="app"
        ), "override app name"
        assert obj.processor_name() == tracing.Breadcrumb(
            application_name="nested", processor_name="proc"
        ), "nested decorators are merged"

        # verify that the decorators work
        assert obj.repository_name().repository_name == "repo"
        assert obj.database_name().database_name == "db"
        assert obj.instance_name().instance_name == "inst"
        assert obj.provider_name().provider_name == "prov"
        assert obj.country().country == "MX"
        assert obj.resource().resource == "res"
        assert obj.action().action == "yes"
        assert obj.status_code().status_code == "200"

        assert obj.not_tracked() == tracing.Breadcrumb()

        assert obj.override_app(act="kwargs_action") == tracing.Breadcrumb(
            application_name="nested", action="kwargs_action"
        ), "extract parameter `action` from kwargs"

        assert obj.override_app(
            act="kwargs_action", opt_resource="res_name"
        ) == tracing.Breadcrumb(
            application_name="nested", action="kwargs_action", resource="res_name"
        ), "include optional param `action` if specified"

        assert obj.override_app(
            act="kwargs_action", opt_resource="res_name", opt_app="override_app"
        ) == tracing.Breadcrumb(
            application_name="override_app", action="kwargs_action", resource="res_name"
        ), "override existing `application_name` with optional param"

        assert obj.override_app(
            act="kwargs_action", opt_resource={}
        ) == tracing.Breadcrumb(
            application_name="nested", action="kwargs_action"
        ), "ignores parameter if it is not the right type"

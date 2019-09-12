from typing import Any
from app.commons.routing import (
    reset_breadcrumbs,
    add_breadcrumb,
    set_resolved_route,
    get_resolved_route,
)


def test_breadcrumbs():
    scope = {}

    breadcrumbs = reset_breadcrumbs(scope)
    assert breadcrumbs == []

    add_breadcrumb(scope, "abc")
    add_breadcrumb(scope, "easy")
    add_breadcrumb(scope, "as")
    add_breadcrumb(scope, "123")

    assert breadcrumbs == ["abc", "easy", "as", "123"]

    assert reset_breadcrumbs(scope) == []


def test_resolved_routes():
    assert get_resolved_route({}) is None

    scope = {}
    assert get_resolved_route(scope) is None
    default: Any = {}
    assert get_resolved_route(scope, default) is default

    route: Any = {}
    set_resolved_route(scope, route)
    assert get_resolved_route(scope) is route

    new_route: Any = {}
    set_resolved_route(scope, new_route)
    assert get_resolved_route(scope) is not route
    assert get_resolved_route(scope) is new_route

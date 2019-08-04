from fastapi import routing as fastapi_routing
from typing import Callable, List
from starlette import routing as starlette_routing
from starlette.types import ASGIApp, Receive, Scope, Send

"""
Override the FastAPI/Starlette routing decorators so that we can track the hierarchy
of routes in the request path.
"""

Breadcrumbs = List[str]
BREADCRUMB_SCOPE_KEY = "routing_breadcrumbs"


def reset_breadcrumbs(scope: Scope) -> Breadcrumbs:
    """
    This should only be called once in the request flow, in the root application.
    """
    scope[BREADCRUMB_SCOPE_KEY] = []
    return scope[BREADCRUMB_SCOPE_KEY]


def add_breadcrumb(scope: Scope, crumb: str):
    """
    Used in routers to append crumbs to the breadcrumbs list.
    """
    if BREADCRUMB_SCOPE_KEY not in scope:
        reset_breadcrumbs(scope)
    breadcrumbs: Breadcrumbs = scope[BREADCRUMB_SCOPE_KEY]
    breadcrumbs.append(crumb)


class APIRouter(fastapi_routing.APIRouter):
    def add_api_route(self, path: str, endpoint: Callable, **kwargs) -> None:
        # ensure we use our subclassed APIRoute
        route = APIRoute(path, endpoint=endpoint, **kwargs)
        self.routes.append(route)

    def mount(self, path: str, app: ASGIApp, name: str = None) -> None:
        # ensure we use our subclassed Mount
        route = Mount(path, app=app, name=name)
        self.routes.append(route)


class APIRoute(fastapi_routing.APIRoute):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # for routers (included nested routers), they get merged together
        add_breadcrumb(scope, f"/{self.name}")
        await super().__call__(scope, receive, send)


class Mount(starlette_routing.Mount):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # for mounted applications, include the mount path in breadcrumbs
        add_breadcrumb(scope, self.path)
        await super().__call__(scope, receive, send)

from typing import Any, Dict, Type, Union, Optional

from fastapi import FastAPI, Header
from fastapi.params import Depends
from pydantic import BaseModel
from fastapi import routing as fastapi_routing, params
from typing import Callable, List, Mapping, Sequence
from starlette import routing as starlette_routing
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.types import ASGIApp, Receive, Scope, Send

from app.commons.api.models import PaymentErrorResponseBody

"""
Override the FastAPI/Starlette routing decorators so that we can track the hierarchy
of routes in the request path.
"""

Breadcrumbs = List[str]
BREADCRUMB_SCOPE_KEY = "routing_breadcrumbs"
RESOLVED_ROUTE_KEY = "routing_resolved_route"


def reset_breadcrumbs(scope: Scope) -> Breadcrumbs:
    """
    This should only be called once in the request flow, in the root application.
    """
    scope[BREADCRUMB_SCOPE_KEY] = []
    return scope[BREADCRUMB_SCOPE_KEY]


def get_endpoint_breadcrumbs(scope: Scope) -> Optional[Breadcrumbs]:
    return scope.get(BREADCRUMB_SCOPE_KEY, None)


def add_breadcrumb(scope: Scope, crumb: str):
    """
    Used in routers to append crumbs to the breadcrumbs list.
    """
    if BREADCRUMB_SCOPE_KEY not in scope:
        reset_breadcrumbs(scope)
    breadcrumbs: Breadcrumbs = scope[BREADCRUMB_SCOPE_KEY]
    breadcrumbs.append(crumb)


def set_resolved_route(scope: Scope, route: "APIRoute"):
    scope[RESOLVED_ROUTE_KEY] = route


def get_resolved_route(
    scope: Scope, default: Optional["APIRoute"] = None
) -> Optional["APIRoute"]:
    return scope.get(RESOLVED_ROUTE_KEY, default)


def group_routers(
    routers: List[fastapi_routing.APIRouter],
    dependencies: Sequence[params.Depends] = None,
) -> fastapi_routing.APIRouter:
    grouped_router = APIRouter()
    for router in routers:
        grouped_router.include_router(router=router, dependencies=dependencies)

    return grouped_router


def group_routers_with_path_prefix(
    prefix_to_routers: Mapping[str, fastapi_routing.APIRouter]
) -> fastapi_routing.APIRouter:
    grouped_router = APIRouter()
    for prefix, router in prefix_to_routers.items():
        grouped_router.include_router(router, prefix=prefix)

    return grouped_router


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
        set_resolved_route(scope, self)
        await super().__call__(scope, receive, send)


class Mount(starlette_routing.Mount):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # for mounted applications, include the mount path in breadcrumbs
        add_breadcrumb(scope, self.path)
        await super().__call__(scope, receive, send)


class ApiRouterBuilder:
    """
    Help class to group multiple sibling routers with a root ApiRouter and:
    1. apply common dependencies, e.g.: headers, auth
    2. apply common response model contracts
    3. include grouped router into a FastApi app
    """

    _prefix_to_router: Dict[str, fastapi_routing.APIRouter]
    _routers: List[fastapi_routing.APIRouter]
    _common_dependencies: List[Depends]
    _common_responses: Dict[Union[int, str], Dict[str, Any]]

    def __init__(self):
        self._prefix_to_router = {}
        self._routers = []
        self._common_dependencies = []
        self._common_responses = {}

    def add_sub_routers_with_prefix(
        self, prefix_to_router: Dict[str, fastapi_routing.APIRouter]
    ) -> "ApiRouterBuilder":
        self._prefix_to_router.update(prefix_to_router)

        return self

    def add_sub_routers(self, *routers: fastapi_routing.APIRouter):
        self._routers.extend(routers)
        return self

    def add_common_dependencies(self, *deps: Callable) -> "ApiRouterBuilder":
        for dep in deps:
            self._common_dependencies.append(Depends(dep))
        return self

    def add_common_responses(
        self, status_code_to_model: Dict[int, Type[BaseModel]]
    ) -> "ApiRouterBuilder":
        for status, model in status_code_to_model.items():
            self._common_responses[status] = {"model": model}
        return self

    def attach_to_app(self, app: FastAPI):
        app.include_router(
            self.as_router(),
            dependencies=self._common_dependencies,
            responses=self._common_responses,
        )

    def as_router(self) -> APIRouter:
        root_router: APIRouter = APIRouter()
        for prefix, router in self._prefix_to_router.items():
            root_router.include_router(router, prefix=prefix)
        for router in self._routers:
            root_router.include_router(router)
        return root_router


def _correlation_id_header(x_correlation_id: str = Header("")):
    """
    Use FastApi Header injection trick to define "x-correlation-id" head in openapi model
    """
    pass


def default_payment_router_builder() -> ApiRouterBuilder:
    """
    create a default payment router builder which already contains common components defined as:
    1. "x-correlation-id" header model
    2. http-500 internal error response model
    3. http-422 validation error response model
    :return: default ApiRouterBuilder
    """
    return (
        ApiRouterBuilder()
        .add_common_dependencies(_correlation_id_header)
        .add_common_responses(
            {
                HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorResponseBody,
                HTTP_422_UNPROCESSABLE_ENTITY: PaymentErrorResponseBody,
            }
        )
    )

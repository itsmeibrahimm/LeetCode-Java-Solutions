from typing import Dict, cast

from app.commons.routing import APIRoute, APIRouter


def validate_router_definition(router: APIRouter):
    """
    Utility function to check whether an APIRouter is well defined
    """
    #  Check if all routes of a router has defined response_model
    #  Check if all routes of a router has defined operation_id

    operation_id_to_path: Dict[str, str] = {}

    for route in router.routes:
        route = cast(APIRoute, route)

        assert route.response_model, (
            f"response_model is not properly set for route path={route.path}, "
            f"without setting it, OpenAPI spec won't include your response model!"
        )

        assert route.operation_id, (
            f"operation_id is not properly set of route path={route.path}, "
            f"without setting it, OpenAPI generated client will have confusing interface name!"
        )

        assert route.operation_id not in operation_id_to_path, (
            f"duplicated operation id found! "
            f"same operation id is assigned to path={operation_id_to_path[route.operation_id]} and path={route.path}"
        )
        operation_id_to_path[route.operation_id] = route.path

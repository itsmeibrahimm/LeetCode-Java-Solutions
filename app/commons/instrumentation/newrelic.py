import newrelic.agent
import fastapi
import starlette.exceptions

from contextlib import contextmanager
from typing import Optional
from starlette.requests import Request
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.application import Application, application_instance
from newrelic.api.transaction import current_transaction

from app.commons.routing import get_resolved_route
from app.commons.context.req_context import get_context_from_req


def transaction_params_from_request(request: Request):
    # https://docs.newrelic.com/docs/agents/python-agent/python-agent-api/webtransaction
    # from the ASGI spec
    # https://github.com/django/asgiref/blob/master/specs/www.rst#L56
    return {
        "framework": ("fastapi", fastapi.__version__),
        # "name": "",
        "group": "Python/ASGI",
        "scheme": request.scope.get("scheme", "http"),
        "host": request.headers.get("host"),
        "request_method": request.method,
        "request_path": request.scope.get("path", ""),
        "query_string": request.scope.get("query_string"),
        "headers": request.headers,
    }


def web_transaction_from_request(request: Request) -> Optional[WebTransaction]:
    request_params = transaction_params_from_request(request)
    return web_transaction(**request_params)


def set_transaction_name_from_request(request: Request, *, priority=5):
    route = get_resolved_route(request.scope)
    if route:
        transaction_name = f"{route.endpoint.__module__}.{route.name}"
        newrelic.agent.set_transaction_name(transaction_name, priority=priority)


def set_request_id_from_request(request: Request):
    req_context = get_context_from_req(request)
    newrelic.agent.add_custom_parameter("req_id", str(req_context.req_id))
    if req_context.correlation_id is not None:
        newrelic.agent.add_custom_parameter(
            "correlation_id", str(req_context.correlation_id)
        )


# newrelic/api/web_transaction.py
def web_transaction(
    framework=None,
    application=None,
    name=None,
    group=None,
    scheme=None,
    host=None,
    port=None,
    request_method=None,
    request_path=None,
    query_string=None,
    headers=None,
) -> Optional[WebTransaction]:
    """
    based on newrelic.api.web_transaction.WSGIApplicationWrapper
    """
    # don't open another transaction
    transaction = current_transaction(active_only=False)
    if transaction:
        return None

    if type(application) != Application:
        _application = application_instance(application)
    else:
        _application = application

    transaction = WebTransaction(
        application=_application,
        name=name,
        group=group,
        scheme=scheme,
        host=host,
        port=port,
        request_method=request_method,
        request_path=request_path,
        query_string=query_string,
        headers=headers,
    )
    if framework:
        transaction.add_framework_info(name=framework[0], version=framework[1])

    return transaction


@contextmanager
def record_exception():
    try:
        # exceptions need to be handled in the context of a WebTransaction
        yield
    except Exception as exc:
        # ignore handled exceptions
        if not isinstance(exc, starlette.exceptions.HTTPException):
            newrelic.agent.record_exception(exc)
        # do not suppress the exception
        raise

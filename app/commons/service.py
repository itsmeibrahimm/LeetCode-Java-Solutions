from abc import ABCMeta

from app.commons.context.app_context import AppContext, get_context_from_app
from app.commons.context.req_context import (
    ReqContext,
    get_context_from_req,
    get_logger_from_req,
)

from starlette.requests import Request
from structlog.stdlib import BoundLogger


class BaseService(metaclass=ABCMeta):
    """
    Base class for all Service dependencies, using dependency injection

    ::

        class MyService(BaseService):
            def __init__(self, request: Request):
                super().__init__(request)
                # Service initialization here
                ...

        @app.get('/api/v1/obj')
        def get_obj(id: int, service: MyService = Depends()):
            ...
    """

    service_name = "payment-service"
    app_context: AppContext
    req_context: ReqContext
    log: BoundLogger

    def __init__(self, request: Request):
        self.app_context = get_context_from_app(request.app)
        self.req_context = get_context_from_req(request)
        self.log = get_logger_from_req(request)

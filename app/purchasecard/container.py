from fastapi import Depends

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import ReqContext, get_context_from_req
from app.purchasecard.core.user.processor import UserProcessor
from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from structlog.stdlib import BoundLogger


class PurchaseCardContainer:

    app_context: AppContext
    req_context: ReqContext

    def __init__(
        self,
        req_context: ReqContext = Depends(get_context_from_req),
        app_context: AppContext = Depends(get_global_app_context),
    ):
        self.app_context = app_context
        self.req_context = req_context

    @property
    def marqeta_client(self) -> MarqetaProviderClient:
        return self.app_context.marqeta_client

    @property
    def logger(self) -> BoundLogger:
        return self.req_context.log

    @property
    def user_processor(self) -> UserProcessor:
        return UserProcessor(marqeta_client=self.marqeta_client, logger=self.logger)

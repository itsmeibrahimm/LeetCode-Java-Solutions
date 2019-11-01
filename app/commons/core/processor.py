from abc import ABC, abstractmethod
from structlog.stdlib import BoundLogger
from typing import Generic, Optional, TypeVar, Union

from pydantic import BaseModel

from app.commons.api.models import PaymentException
from app.commons.context.logger import get_logger
from app.commons.core.errors import PaymentError


class OperationResponse(BaseModel):
    pass


class OperationRequest(BaseModel):
    pass


RespT = TypeVar("RespT", bound=OperationResponse)
ReqT = TypeVar("ReqT", bound=OperationRequest)


class AsyncOperation(ABC, Generic[ReqT, RespT]):
    """
    Abstraction of an async operation running a specific set of business logic
    """

    logger: BoundLogger
    request: ReqT

    def __init__(self, request: ReqT, logger: Optional[BoundLogger] = None):
        self.logger = logger or get_logger(__name__)
        self.request = request

    async def execute(self) -> RespT:
        try:
            return await self._execute()
        except Exception as internal_exec:
            # todo: Kevin to fix PaymentException. It should not be PaymentException.
            if isinstance(internal_exec, PaymentException):
                raise
            self.logger.error(
                f"{__name__}: handling internal exception.",
                internal_exception=str(internal_exec),
            )
            exec_or_result = self._handle_exception(internal_exec)
            if isinstance(exec_or_result, Exception):
                raise
            return exec_or_result

    @abstractmethod
    async def _execute(self) -> RespT:
        """
        implement actual business logic for this processor here
        """
        pass

    @abstractmethod
    def _handle_exception(
        self,
        internal_exec: Exception
        # todo: Kevin, remove PaymentException
    ) -> Union[PaymentException, PaymentError, RespT]:
        """
        define how do handler or translate exceptions raised within this processor and its dependencies
        """
        pass

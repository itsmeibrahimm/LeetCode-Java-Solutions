from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar, Union

from pydantic import BaseModel

from app.commons.context.logger import Log, get_logger
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

    logger: Log
    request: ReqT

    def __init__(self, request: ReqT, logger: Optional[Log] = None):
        self.logger = logger or get_logger(__name__)
        self.request = request

    async def execute(self) -> RespT:
        try:
            return await self._execute()
        except BaseException as internal_exec:
            self.logger.info(f"{__name__}: handling error={str(internal_exec)}")
            exec_or_result = self._handle_exception(internal_exec)
            if isinstance(exec_or_result, BaseException):
                raise exec_or_result
            return exec_or_result

    @abstractmethod
    async def _execute(self) -> RespT:
        """
        implement actual business logic for this processor here
        """
        pass

    @abstractmethod
    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentError, RespT]:
        """
        define how do handler or translate exceptions raised within this processor and its dependencies
        """
        pass

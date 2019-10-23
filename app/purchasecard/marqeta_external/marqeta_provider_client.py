from typing import Optional, Any

import aiohttp
from aiohttp import BasicAuth
from pydantic import BaseModel

from app.purchasecard.marqeta_external.models import (
    MarqetaProviderCreateUserRequest,
    MarqetaProviderCreateUserResponse,
)
import app.purchasecard.marqeta_external.error as marqeta_error

SAME_EMAIL_ERROR_CODE = "400057"


class MarqetaClientSettings(BaseModel):
    marqeta_base_url: str
    username: str
    password: str
    program_fund_token: str


class MarqetaProviderClient:
    """
    Abstraction of marqeta api communication

    TODO: Currently as a skeleton for @jasmine-tea
    """

    _marqeta_base_url: str
    _program_fund_token: str
    _username: str
    _password: str
    _session: aiohttp.ClientSession
    _default_timeout: float

    def __init__(
        self,
        marqeta_client_settings: MarqetaClientSettings,
        session: aiohttp.ClientSession,
        default_timeout: float = 10,
    ):
        self._marqeta_base_url = marqeta_client_settings.marqeta_base_url
        self._program_fund_token = marqeta_client_settings.program_fund_token
        self._username = marqeta_client_settings.username
        self._password = marqeta_client_settings.password
        self._session = session
        self._default_timeout = default_timeout

    def _get_auth(self) -> BasicAuth:
        return BasicAuth(login=self._username, password=self._password)

    @classmethod
    async def _handle_status(cls, response_status: int, json_resp_body: Any):
        if response_status != 201:
            if response_status == 400:
                raise marqeta_error.MarqetaBadRequest(json_resp_body)
            elif response_status == 409:
                raise marqeta_error.MarqetaResourceAlreadyCreated(json_resp_body)
            else:
                raise marqeta_error.MarqetaAPIError(json_resp_body)

    async def create_marqeta_user(
        self, req: MarqetaProviderCreateUserRequest, timeout: Optional[float] = None
    ) -> MarqetaProviderCreateUserResponse:
        """
        :param req:
        :param timeout:
        :return:
        """
        aio_timeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))

        url = self._marqeta_base_url + "users"

        async with self._session.post(
            url=url, auth=self._get_auth(), json=req.dict(), timeout=aio_timeout
        ) as resp:
            try:
                json_resp_body = await resp.json()
                await self._handle_status(resp.status, json_resp_body)

            except marqeta_error.MarqetaBadRequest:
                if json_resp_body["error_code"] == SAME_EMAIL_ERROR_CODE:
                    raise marqeta_error.DuplicateEmail()

            return MarqetaProviderCreateUserResponse(**json_resp_body)

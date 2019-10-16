from typing import Optional, Tuple

import aiohttp
from pydantic import BaseModel

from app.purchasecard.marqeta_external.models import MarqetaProviderCreateUserRequest


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

    def _get_auth(self) -> Tuple[Optional[str], Optional[str]]:
        return self._username, self._password

    async def create_marqeta_user(
        self, req: MarqetaProviderCreateUserRequest, timeout: Optional[float] = None
    ):
        """
        TODO: @jasmine-tea remember to add a test!
        :param req:
        :param timeout:
        :return:
        """
        aiotimeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))

        url = self._marqeta_base_url + "users"

        async with self._session.post(
            url, auth=self._get_auth(), data=req.dict(), timeout=aiotimeout
        ) as resp:
            return resp.json()

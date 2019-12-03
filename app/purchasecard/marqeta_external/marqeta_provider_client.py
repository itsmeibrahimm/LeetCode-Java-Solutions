from typing import Optional, Any

import aiohttp
from aiohttp import BasicAuth
from pydantic import BaseModel

from app.purchasecard.marqeta_external.models import (
    MarqetaProviderCreateUserRequest,
    MarqetaProviderCreateUserResponse,
    MarqetaProviderGetCardRequest,
    MarqetaProviderCard,
)
import app.purchasecard.marqeta_external.errors as marqeta_error

SAME_EMAIL_ERROR_CODE = "400057"
CANNOT_MOVE_CARD_TO_NEW_CARD_HOLDER = "400089"
NEVER_ACTIVATED = "400092"


class MarqetaClientSettings(BaseModel):
    marqeta_base_url: str
    username: str
    password: str
    program_fund_token: str
    card_token_prefix_cutover_id: int


class MarqetaProviderClient:
    """
    Abstraction of marqeta api communication

    TODO: Currently as a skeleton for @jasmine-tea
    """

    _marqeta_base_url: str
    _program_fund_token: str
    _username: str
    _password: str
    _card_token_prefix_cutover_id: int
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
        self._card_token_prefix_cutover_id = (
            marqeta_client_settings.card_token_prefix_cutover_id
        )

        self._session = session
        self._default_timeout = default_timeout

    def get_auth(self) -> BasicAuth:
        return BasicAuth(login=self._username, password=self._password)

    def get_url(self, endpoint) -> str:
        return self._marqeta_base_url + endpoint

    @classmethod
    async def _handle_status_post(cls, response_status: int, json_resp_body: Any):
        if response_status != 201:
            if response_status == 400:
                raise marqeta_error.MarqetaBadRequest(json_resp_body)
            elif response_status == 409:
                raise marqeta_error.MarqetaResourceAlreadyCreated(json_resp_body)
            else:
                raise marqeta_error.MarqetaAPIError(json_resp_body)

    @classmethod
    async def _handle_status_get(cls, response_status: int, json_resp_body: Any):
        if response_status != 200:
            if response_status == 400:
                raise marqeta_error.MarqetaBadRequest(json_resp_body)
            elif response_status == 404:
                raise marqeta_error.MarqetaResourceNotFound(json_resp_body)
            else:
                raise marqeta_error.MarqetaAPIError(json_resp_body)

    def get_card_token_prefix_cutover_id(self) -> int:
        return self._card_token_prefix_cutover_id

    async def create_marqeta_user(
        self, req: MarqetaProviderCreateUserRequest, timeout: Optional[float] = None
    ) -> MarqetaProviderCreateUserResponse:
        """
        :param req: MarqetaProviderCreateUserRequest
        :param timeout: Optional[float] = None
        :return: MarqetaProviderCreateUserResponse
        """
        aio_timeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))

        url = self._marqeta_base_url + "users"

        async with self._session.post(
            url=url, auth=self.get_auth(), json=req.dict(), timeout=aio_timeout
        ) as resp:
            try:
                json_resp_body = await resp.json()
                await self._handle_status_post(resp.status, json_resp_body)

            except marqeta_error.MarqetaBadRequest:
                if json_resp_body["error_code"] == SAME_EMAIL_ERROR_CODE:
                    raise marqeta_error.DuplicateEmail()

            return MarqetaProviderCreateUserResponse(**json_resp_body)

    async def get_marqeta_card_and_verify(
        self, req: MarqetaProviderGetCardRequest, timeout: Optional[float] = None
    ) -> MarqetaProviderCard:
        """
        :param req: MarqetaProviderGetCardRequest
        :param timeout: Optional[float] = None
        :return: MarqetaProviderCard
        """
        aio_timeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))

        url = self.get_url("cards/{}".format(req.token))

        async with self._session.get(
            url=url, auth=self.get_auth(), timeout=aio_timeout
        ) as resp:
            json_resp_body = await resp.json()
            await self._handle_status_get(resp.status, json_resp_body)
            card = MarqetaProviderCard(**json_resp_body)
            if card.last_four != req.last4:
                raise marqeta_error.MarqetaBadRequest(
                    "last4 {} does not match token {}".format(card.last_four, req.last4)
                )
            return card

    async def update_card_activation(
        self, token: str, active: bool, timeout: Optional[float] = None
    ) -> Optional[MarqetaProviderCard]:
        """
        :param token: card token
        :param active: bool
        :param timeout: float
        :return: MarqetaProviderCard
        """
        aio_timeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))

        if active:
            suffix = "activate"
        else:
            suffix = "deactivate"

        url = self._marqeta_base_url + "cards/{}/{}".format(token, suffix)

        async with self._session.put(
            url=url, auth=self.get_auth(), json={}, timeout=aio_timeout
        ) as resp:
            json_resp_body = await resp.json()
            if resp.status != 200:
                e = marqeta_error.MarqetaAPIError()
                if (
                    "error_code" in json_resp_body
                    and json_resp_body["error_code"] == NEVER_ACTIVATED
                ):
                    return None
                raise e
            card = MarqetaProviderCard(**json_resp_body)
            return card

    async def update_card_user_token(
        self, token: str, user_token: str, timeout: Optional[float] = None
    ) -> MarqetaProviderCard:
        """
        :param token: card token
        :param user_token: str
        :param timeout: float
        :return: MarqetaProviderCard
        """
        aio_timeout = aiohttp.ClientTimeout(total=(timeout or self._default_timeout))
        url = self._marqeta_base_url + "cards/{}".format(token)
        async with self._session.put(
            url=url,
            auth=self.get_auth(),
            json={"user_token": user_token},
            timeout=aio_timeout,
        ) as resp:
            json_resp_body = await resp.json()

            if resp.status != 200:
                if (
                    "error_code" in json_resp_body
                    and json_resp_body["error_code"]
                    == CANNOT_MOVE_CARD_TO_NEW_CARD_HOLDER
                ):
                    raise marqeta_error.MarqetaCannotMoveCardToNewCardHolderError(
                        resp.content
                    )
                raise marqeta_error.MarqetaAPIError(resp.content)

            return MarqetaProviderCard(**json_resp_body)

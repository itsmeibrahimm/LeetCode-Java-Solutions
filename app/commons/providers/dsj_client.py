from typing import Dict, Any
from datetime import datetime, timedelta
import aiohttp

from app.commons.context.logger import get_logger

DEFAULT_HTTP_REQUEST_TIMEOUT = 10

# tentative before hooking up dsj client with req context
dsj_client_logger = get_logger("dsj_client")


class DSJAuthException(Exception):
    pass


class DSJRESTCallException(Exception):
    pass


class DSJClient:
    """
    DSJ client built on top of aiohttp
    """

    auth_jwt_local_state: Dict[str, Any] = {
        "token": None,
        "cache_expires_at": datetime.utcnow(),
    }

    client_config: Dict[str, Any] = {
        "base_url": None,
        "email": None,
        "password": None,
        "jwt_token_ttl": 0.0,
    }

    def __init__(self, client_config: Dict[str, Any]):
        self.client_config = client_config

    def _dsj_uri(self, uri) -> str:
        return self.client_config.get("base_url") + uri

    async def _fetch_request_token(self) -> Dict[str, Any]:
        """
        Fetch DSJ JWT token from DSJ auth URI

        :return:
        """

        jwt_token_auth_url = self._dsj_uri("/v2/auth/token/")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                jwt_token_auth_url,
                data={
                    "email": self.client_config.get("email"),
                    "password": self.client_config.get("password"),
                },
            ) as resp:
                if resp.status != 200:
                    raise DSJAuthException(
                        f"DSJ auth failed: {resp.status} {resp.reason}"
                    )
                return await resp.json()

    async def get_token(self) -> str:
        """
        Get DSJ JWT token

        :return: a valid jwt token
        """

        # invalidate cached jwt token if it has expired
        jwt_expired_at = self.auth_jwt_local_state.get(
            "cache_expires_at", datetime.utcnow()
        )
        if jwt_expired_at <= datetime.utcnow():
            self.auth_jwt_local_state["token"] = None

        # refresh jwt token if none or expired
        if not self.auth_jwt_local_state.get("token"):
            new_token = await self._fetch_request_token()
            self.auth_jwt_local_state["token"] = new_token.get("token")
            self.auth_jwt_local_state[
                "cache_expires_at"
            ] = datetime.utcnow() + timedelta(
                seconds=self.client_config.get("jwt_token_ttl", 0.0)
            )

        # return the token
        return self.auth_jwt_local_state["token"]

    async def get(
        self,
        uri: str,
        params: Dict[str, str],
        timeout_sec: int = DEFAULT_HTTP_REQUEST_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        DSJ REST get method (wrap around aiohttp get)

        :param uri:
        :param params:
        :param timeout_sec: default 10 seconds for the request session
        :param log
        :return:
        """

        token = await self.get_token()
        headers = {"Authorization": f"JWT {token}"}
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(self._dsj_uri(uri), params=params) as resp:
                if resp.status != 200:
                    # TODO: provide specific HTTP error handlers
                    raise DSJRESTCallException(
                        f"DSJ REST call failed: {resp.status} {resp.reason}"
                    )
                try:
                    return await resp.json()
                except aiohttp.client_exceptions.ContentTypeError:
                    dsj_client_logger.warning("200 OK, but can not parse JSON")
                    return {}

    async def post(
        self,
        uri: str,
        data: Dict[str, str],
        timeout_sec: int = DEFAULT_HTTP_REQUEST_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        DSJ REST post method (wrap around aiohttp post)

        :param uri:
        :param data:
        :param timeout_sec: default 10 seconds for the request session
        :param log
        :return:
        """

        token = await self.get_token()
        headers = {"Authorization": f"JWT {token}"}
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.post(self._dsj_uri(uri), data=data) as resp:
                if resp.status != 200:
                    # TODO: provide specific HTTP error handlers
                    raise DSJAuthException(
                        f"DSJ REST call failed: {resp.status} {resp.reason}"
                    )
                try:
                    return await resp.json()
                except aiohttp.client_exceptions.ContentTypeError:
                    dsj_client_logger.warning("200 OK, but can not parse JSON")
                    return {}

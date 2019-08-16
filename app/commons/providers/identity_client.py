from abc import ABC, abstractmethod

import aiohttp
from cachetools import TTLCache
from fastapi import HTTPException

from app.commons.providers.identity_models import VerifyTokenResponse

CORRELATION_ID_KEY = "x-correlation-id"
TOKEN_KEY = "authorization"


class ApiKeyVerificationError(Exception):
    pass


class IdentityClientInterface(ABC):
    @abstractmethod
    async def verify_api_key_with_grpc(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        ...

    @abstractmethod
    async def verify_api_key_with_http(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        ...


class StubbedIdentityClient(IdentityClientInterface):
    """
    Used for testing to bypass authorization/authentication
    """

    async def verify_api_key_with_grpc(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        pass

    async def verify_api_key_with_http(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        pass


class IdentityClient(IdentityClientInterface):
    """
    Handles communication with Identity Service and serves as a L0 cache for returned results if needed
    """

    __verify_url: str = "{}/api/v1/verify/{}"
    __ttl_cache: TTLCache
    __default_ttl_cache_size: int

    def __init__(
        self,
        http_endpoint: str,
        grpc_endpoint: str,
        cache_ttl: int = 60 * 3,
        ttl_cache_size: int = 10,
    ):
        """

        :param http_endpoint:
        :param grpc_endpoint:
        :param cache_ttl:
        :param ttl_cache_size:
        """
        self.http_endpoint = http_endpoint
        self.grpc_endpoint = grpc_endpoint
        self.__ttl_cache = TTLCache(ttl=cache_ttl, maxsize=ttl_cache_size)

    async def verify_api_key_with_grpc(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        """
        This function is intended to use the grpc Identity Service endpoint to verify token. Currently leaving as a stub
        in case we need it.
        :param service_id: service_id of payment-service issued by Identity service
        :param api_key: the client api key passed from one of our upstream clients
        :param correlation_id: usually our own unique request id (or a global id if the framework is in place)
        :return:
        """
        # channel = Channel(endpoint, port)
        # client = authentication_grpc.AuthenticationServiceStub(channel)
        # token_info = auth_pb2.TokenInfoRequest()
        # token_info.service_id = service_id
        # # This doesn't work b/c clients need to generate
        # reply: auth_pb2.TokenInfoResponse = await client.GetTokenInfo(request=token_info,
        #                                                               metadata=(
        #                                                                   (TOKEN_KEY, api_key),
        #                                                                   (CORRELATION_ID_KEY, correlation_id)),
        #                                                               )
        # channel.close()
        # return reply
        raise NotImplementedError(
            "grpclib integration is incomplete, proto generation needs to be enhanced"
        )

    async def verify_api_key_with_http(
        self, service_id: int, api_key: str, correlation_id: str
    ) -> VerifyTokenResponse:
        """
        Verifies an api key issued using the provided service_id. Only services with a valid api key will succeed
        and return a VerifyTokenResponse object
        :param service_id: service_id of payment-service issued by Identity service
        :param api_key: the client api key passed from one of our upstream clients
        :param correlation_id: usually our own unique request id (or a global id if the framework is in place)
        :return:
        :raises HTTPException
        """
        result_from_cache = self._verify_from_cache(api_key)
        if result_from_cache:
            return result_from_cache

        url = self.__class__.__verify_url.format(self.http_endpoint, int(service_id))
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers={TOKEN_KEY: api_key, CORRELATION_ID_KEY: correlation_id}
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail=resp.reason)
                json = await resp.json()
                verify_token_response = VerifyTokenResponse(**json)
                self._cache_response(api_key, verify_token_response)
                return verify_token_response

    def _cache_response(self, api_key: str, response: VerifyTokenResponse):
        if response.client_id and api_key:
            self.__ttl_cache[api_key] = response

    def _verify_from_cache(self, api_key: str):
        result_from_cache: VerifyTokenResponse = self.__ttl_cache.get(
            key=api_key, default=None
        )
        if result_from_cache:
            result_from_cache.from_cache = True
        return result_from_cache

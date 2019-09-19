from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.commons.auth.service_auth import ApiSecretRouteAuthorizer
from app.commons.providers.identity_client import (
    IdentityBaseError,
    InternalIdentityBaseError,
    ConnectionError,
    ClientReponseError,
    ClientTimeoutError,
    UnauthorizedError,
)


class WTFException(Exception):
    ...


class TestApiSecretRouteAuthorizerExceptionHandling:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def mock_request_with_fake_ids_client(self, dummy_app_context):
        mock_request = MagicMock()

        def fake_get(attr):
            if attr == "context":
                return dummy_app_context
            return self.get(attr)

        mock_request.app.extra.get.side_effect = fake_get
        mock_request.app.extra.context = dummy_app_context
        return mock_request

    async def test_unknown_exception(self, mock_request_with_fake_ids_client):
        mock_identity_client = (
            mock_request_with_fake_ids_client.app.extra.context.identity_client
        )
        mock_identity_client.verify_api_key_with_http.side_effect = WTFException()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

    async def test_known_exceptions(self, mock_request_with_fake_ids_client):
        mock_identity_client = (
            mock_request_with_fake_ids_client.app.extra.context.identity_client
        )
        mock_identity_client.verify_api_key_with_http.side_effect = WTFException()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = IdentityBaseError()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = (
            InternalIdentityBaseError()
        )

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = ClientReponseError()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = ConnectionError()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = ClientTimeoutError()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

        mock_identity_client.verify_api_key_with_http.side_effect = UnauthorizedError()

        with pytest.raises(HTTPException):
            await ApiSecretRouteAuthorizer(123)(mock_request_with_fake_ids_client)

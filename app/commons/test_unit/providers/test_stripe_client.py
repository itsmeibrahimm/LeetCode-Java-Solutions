from unittest import mock

import pytest
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.core.errors import (
    PGPConnectionError,
    PGPApiError,
    PGPRateLimitError,
    PGPAuthenticationError,
    PGPAuthorizationError,
    PGPIdempotencyError,
    PGPInvalidRequestError,
    PGPResourceNotFoundError,
)
from app.commons.providers.stripe.stripe_models import RetrieveAccountRequest
import stripe.error as stripe_error

from app.payout.test_integration.utils import mock_stripe_account


class TestStripeClient:
    def setup(self):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )

    @pytest.fixture
    def mock_retrieve_stripe_account(self):
        with mock.patch("stripe.Account.retrieve") as mock_retrieve_stripe_account:
            yield mock_retrieve_stripe_account

    def test_retrieve_stripe_account_succeed(self, mock_retrieve_stripe_account):
        stripe_account_id = "acct_xxx"
        mock_retrieve_stripe_account.return_value = mock_stripe_account(
            stripe_account_id=stripe_account_id
        )
        # pass test if succeeded in getting account info from stripe
        try:
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(
                    country="US", account_id=stripe_account_id
                )
            )
        except Exception:
            raise Exception(
                "Retrieve stripe account should not raise exception when successfully"
                " get account info from stripe"
            )

    def test_retrieve_stripe_account_stripe_error_translation(
        self, mock_retrieve_stripe_account
    ):
        # Should return PGPConnectionError when stripe return APIConnectionError
        mock_retrieve_stripe_account.side_effect = stripe_error.APIConnectionError(
            "failed to connect to stripe"
        )

        with pytest.raises(PGPConnectionError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPApiError when stripe return APIError
        mock_retrieve_stripe_account.side_effect = stripe_error.APIError

        with pytest.raises(PGPApiError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPRateLimitError when stripe return RateLimitError
        mock_retrieve_stripe_account.side_effect = stripe_error.RateLimitError

        with pytest.raises(PGPRateLimitError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPAuthenticationError when stripe return AuthenticationError
        mock_retrieve_stripe_account.side_effect = stripe_error.AuthenticationError

        with pytest.raises(PGPAuthenticationError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPAuthorizationError when stripe return PermissionError
        mock_retrieve_stripe_account.side_effect = stripe_error.PermissionError

        with pytest.raises(PGPAuthorizationError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPIdempotencyError when stripe return IdempotencyError
        mock_retrieve_stripe_account.side_effect = stripe_error.IdempotencyError

        with pytest.raises(PGPIdempotencyError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

        # Should return PGPInvalidRequestError if stripe return InvalidRequestError and
        # error_code in PGPInvalidRequestErrorStripeErrorCode
        mock_retrieve_stripe_account.side_effect = stripe_error.InvalidRequestError(
            message="invalid request", param="some param", code="api_key_expired"
        )

        with pytest.raises(PGPInvalidRequestError) as e:
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )
            assert e.user_message == "invalid_message"

        # Should return PGPResourceNotFoundError if stripe return InvalidRequestError and
        # error_code is resource_missing and status code is 404
        mock_retrieve_stripe_account.side_effect = stripe_error.InvalidRequestError(
            message="invalid request",
            param="some param",
            code="resource_missing",
            http_status=404,
        )

        with pytest.raises(PGPResourceNotFoundError):
            self.stripe_client.retrieve_stripe_account(
                request=RetrieveAccountRequest(country="US", account_id="acct_xxx")
            )

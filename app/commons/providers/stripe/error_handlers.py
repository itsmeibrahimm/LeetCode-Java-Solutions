import asyncio
from functools import wraps
import stripe.error as stripe_error

from app.commons.core.errors import (
    PGPApiError,
    PGPConnectionError,
    PGPRateLimitError,
    PGPAuthenticationError,
    PGPAuthorizationError,
    PGPIdempotencyError,
    PGPInvalidRequestError,
    PGPResourceNotFoundError,
)

PGPInvalidRequestErrorStripeErrorCode = [
    "parameters_exclusive",
    "parameter_unknown",
    "parameter_missing",
    "parameter_invalid_string_empty",
    "parameter_invalid_string_blank",
    "parameter_invalid_integer",
    "parameter_invalid_empty",
    "lock_timeout",
    "livemode_mismatch",
    "api_key_expired",
    "url_invalid",
    "tls_version_unsupported",
    "secret_key_required",
    "platform_api_key_expired",
]


def translate_stripe_error(func):
    """Translate Stripe Errors into payment processor layer errors.

    This function maps stripe errors into corresponding payment errors, so that the processor and above layers does not
    need to know the downstream error details. So that it is easy to support multiple providers or swap stripe with
    other providers.

    We should only handle know errors. For unknown errors, should let it bubble up.

    Details stripe error mapping can be found at,
    https://github.com/doordash/money-uml/blob/master/payout/puml-png/processor_layer_errors.png.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            raise Exception(
                "translate_stripe_error decorator can't not used in async function."
            )
        try:
            result = func(*args, **kwargs)
            return result
        # Handle general stripe error
        except stripe_error.APIConnectionError as e:
            raise PGPConnectionError from e
        except stripe_error.APIError as e:
            raise PGPApiError from e
        except stripe_error.RateLimitError as e:
            raise PGPRateLimitError from e
        except stripe_error.AuthenticationError as e:
            raise PGPAuthenticationError from e
        except stripe_error.PermissionError as e:
            raise PGPAuthorizationError from e
        except stripe_error.IdempotencyError as e:
            raise PGPIdempotencyError from e
        except stripe_error.InvalidRequestError as e:
            # Handle general stripe invalid request error
            if e.code in PGPInvalidRequestErrorStripeErrorCode:
                raise PGPInvalidRequestError(e.user_message) from e
            # Handle 404 resource_missing error
            if e.http_status == 404 and e.code == "resource_missing":
                raise PGPResourceNotFoundError from e
            # todo: Leon & Kevin, add more models specific errors mapping

    return wrapper

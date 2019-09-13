import os
import sys
import time
import uuid

from ledger_client.api_client import ApiClient as Ledger
from ledger_client.configuration import Configuration as LedgerConfig
from locust import events
from payin_v0_client.api_client import ApiClient as PayinV0
from payin_v0_client.configuration import Configuration as PayinV0Config
from payin_v1_client.api_client import ApiClient as PayinV1
from payin_v1_client.configuration import Configuration as PayinV1Config
from payout_v0_client.api_client import ApiClient as PayoutV0
from payout_v0_client.configuration import Configuration as PayoutV0Config
from payout_v1_client.api_client import ApiClient as PayoutV1
from payout_v1_client.configuration import Configuration as PayoutV1Config

"""
Monkey match all ApiClient.request(...) interfaces from each OpenApi client
to allow emitting locust load testing metrics
"""

__all__ = [
    "PayoutV0",
    "PayoutV0Config",
    "PayoutV1",
    "PayoutV1Config",
    "PayinV0",
    "PayinV0Config",
    "PayinV1",
    "PayinV1Config",
    "Ledger",
    "LedgerConfig",
]

NoSpecified = ""

_API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", NoSpecified)
_DEFAULT_TIMEOUT_SEC = 5


def monkey_patch_api_client(api_client_cls):
    original_request = api_client_cls.request

    def request(
        self,
        method,
        url,
        query_params=None,
        headers=None,
        post_params=None,
        body=None,
        _preload_content=True,
        _request_timeout=None,
    ):

        correlation_id = f"pressure-{uuid.uuid4()}"
        headers["x-correlation-id"] = correlation_id
        headers["x-api-key"] = _API_KEY
        start_time = time.time()
        try:
            result = original_request(
                self,
                method,
                url,
                query_params=query_params,
                headers=headers,
                post_params=post_params,
                body=body,
                _preload_content=_preload_content,
                _request_timeout=_request_timeout
                if _request_timeout
                else _DEFAULT_TIMEOUT_SEC,
            )
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                request_type=method,
                name=url,
                response_time=total_time,
                response_length=sys.getsizeof(result, 0),
            )
            print(
                f"request-id={result.getheader('x-payment-request-id')} correlation-id={correlation_id} completed in {total_time}ms"
            )
            return result
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            request_id = (
                e.headers.get("x-payment-request-id", None)
                if hasattr(e, "headers")
                else None
            )
            print(
                f"request-id={request_id} correlation-id={correlation_id} failed in {total_time}ms"
            )
            events.request_failure.fire(
                request_type=method, name=url, response_time=total_time, exception=e
            )
            raise

    api_client_cls.request = request


monkey_patch_api_client(PayinV0)
monkey_patch_api_client(PayinV1)
monkey_patch_api_client(PayoutV0)
monkey_patch_api_client(PayoutV1)
monkey_patch_api_client(Ledger)

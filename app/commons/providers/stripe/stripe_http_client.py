import stripe
import requests

from typing import Optional

from requests.adapters import HTTPAdapter

from app.commons.timing import http_client as http_client_timing
from stripe.http_client import HTTPClient, RequestsClient


def set_default_http_client(http_client: Optional[HTTPClient]):
    # note: these are threadsafe, so we can set it up
    # prior to spawning the threadpool
    stripe.default_http_client = http_client


class TimedSession(requests.Session):
    # track timing and response
    @http_client_timing.track_stripe_http_client(stat_name="io.stripe-lib.latency")
    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)
        return response


class TimedRequestsClient(RequestsClient):

    # See https://urllib3.readthedocs.io/en/latest/advanced-usage.html#customizing-pool-behavior
    # and https://laike9m.com/blog/requests-secret-pool_connections-and-pool_maxsize,89/
    # to understand urllib3 connection pooling mechanism
    _max_connection_pool_size: int = 10

    def __init__(
        self,
        timeout=80,  # super class default value
        session=None,
        max_connection_pool_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(timeout, session, **kwargs)
        self._max_connection_pool_size = (
            max_connection_pool_size or self._max_connection_pool_size
        )

    def request(self, method, url, headers, post_data=None):
        if not self._session:
            self._session = TimedSession()
            self._session.mount(
                "https://", HTTPAdapter(pool_maxsize=self._max_connection_pool_size)
            )
            self._session.mount(
                "http://", HTTPAdapter(pool_maxsize=self._max_connection_pool_size)
            )

        return super().request(method, url, headers, post_data=post_data)

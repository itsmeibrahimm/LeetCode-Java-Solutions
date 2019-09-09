import stripe
import requests

from typing import Optional
from app.commons import timing
from stripe.http_client import HTTPClient, RequestsClient


def set_default_http_client(http_client: Optional[HTTPClient]):
    # note: these are threadsafe, so we can set it up
    # prior to spawning the threadpool
    stripe.default_http_client = http_client


class TimedSession(requests.Session):
    # track timing and response
    @timing.track_client_response()
    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)
        return response


class TimedRequestsClient(RequestsClient):
    def request(self, method, url, headers, post_data=None):
        if not self._session:
            self._session = TimedSession()

        return super().request(method, url, headers, post_data=post_data)

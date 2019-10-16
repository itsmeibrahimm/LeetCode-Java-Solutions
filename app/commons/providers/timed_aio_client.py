from aiohttp import ClientSession, ClientResponse

from app.commons.timing.http_client import (
    track_identity_http_client_security_stats,
    track_identity_http_client_timing,
)


class TrackedIdentityClientSession(ClientSession):
    @track_identity_http_client_security_stats(stat_name="security.identity-client")
    @track_identity_http_client_timing(stat_name="io.identity-client.latency")
    async def _request(self, *args, **kwargs):
        client_response: ClientResponse = await super()._request(*args, **kwargs)
        return client_response


class TrackedDsjClientSession(ClientSession):
    @track_identity_http_client_timing(stat_name="io.dsj-client.latency")
    async def _request(self, *args, **kwargs):
        client_response: ClientResponse = await super()._request(*args, **kwargs)
        return client_response


class TrackedMarqetaClientSession(ClientSession):
    @track_identity_http_client_timing(stat_name="io.marqeta-client.latency")
    async def _request(self, *args, **kwargs):
        client_response: ClientResponse = await super()._request(*args, **kwargs)
        return client_response

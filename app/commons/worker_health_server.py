import os

import aiohttp
import typing

from app.commons.context.logger import get_logger

logger = get_logger(__name__)


class HealthServer:
    server: aiohttp.web.Server
    runner: aiohttp.web.ServerRunner
    site: typing.Optional[aiohttp.web.TCPSite]

    def __init__(self):
        async def handler(request):
            logger.info(
                "current payment-service release",
                release_tag=os.getenv("RELEASE_TAG", "unknown"),
            )
            return aiohttp.web.Response(text="OK")

        self.server = aiohttp.web.Server(handler)
        self.runner = aiohttp.web.ServerRunner(self.server)
        self.site = None

    async def start(self, *, port: int = 80):
        await self.runner.setup()

        self.site = aiohttp.web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()

        logger.info("Started health server", extra={"port": port})

    async def stop(self):
        await self.site.stop()
        await self.runner.shutdown()

        logger.info("Stopped health server")

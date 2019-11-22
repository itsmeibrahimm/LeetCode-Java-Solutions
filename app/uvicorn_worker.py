import asyncio
import signal
from typing import Dict, Any
from uvicorn.workers import UvicornWorker as DefaultUvicornWorker


def monkey_patch_uvicorn_server():
    """
    Monkey patch UvicornServer to handle additional unix signals with graceful shutting down

    """
    from uvicorn.main import Server

    # If need more custom signal handling need to add a map structure of {signal: handler}
    additional_signals = {signal.SIGABRT}

    original_install_handler = Server.install_signal_handlers

    def install_more_handler(self: Server):
        """
        Install additional unix signal handler.
        Borrowed from https://github.com/encode/uvicorn/blob/master/uvicorn/main.py#L510
        """
        original_install_handler(self)

        loop = asyncio.get_event_loop()
        try:
            for sig in additional_signals:
                loop.add_signal_handler(sig, self.handle_exit, sig, None)
        except NotImplementedError:
            # Windows
            for sig in additional_signals:
                signal.signal(sig, self.handle_exit)

        self.logger.info(
            f"[UvicornServer] installed additional handlers={additional_signals}"
        )

    Server.install_signal_handlers = install_more_handler


monkey_patch_uvicorn_server()


class UvicornWorker(DefaultUvicornWorker):
    """
    Extended gunicorn worker class from uvicorn.workers.UvicornWorker to allow more flexible configurations
    """

    CONFIG_KWARGS: Dict[str, Any] = {
        "loop": "uvloop",
        "http": "httptools",
        "lifespan": "on",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_worker_max_requests()
        self.log.info(
            f"[UvicornWorker] worker initialized with config={self.config.__dict__}"
        )

    def _configure_worker_max_requests(self):
        """
        configure maximum number of requests handled by single worker before shut down and re-spawn a new one.

        Gunicorn `max_requests` and `max_requests_jitter` were not wired into default uvicorn worker.
        Instead Uvicorn worker uses `limit_max_requests` to set maximum number of requests a single worker
        process can handle before being recycled to prevent memory leak effect

        The base class - `gunicorn.workers.base.Worker` will init `max_requests` from gunicorn configured
        `max_requests` and `max_requets_jitter` see: http://docs.gunicorn.org/en/stable/settings.html#max-requests

        Correspondingly, we directly use Worker::max_requests to set UvicornWorker.limit_max_requests without a separate
        configuration. see: https://www.uvicorn.org/settings/#resource-limits
        """
        self.config.limit_max_requests = self.max_requests
        self.log.info(
            f"configure uvicorn worker limit_max_requests={self.config.limit_max_requests} "
            f"based on gunicorn configured max_requests={self.cfg.max_requests} "
            f"and max_requests_jitter={self.cfg.max_requests_jitter}"
        )

    async def callback_notify(self):
        await super().callback_notify()
        self.log.info(f"[UvicornWorker] (pid: {self.pid}) Heartbeat!")

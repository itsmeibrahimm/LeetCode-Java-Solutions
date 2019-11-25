import asyncio
import signal
from typing import Dict, Any
from uvicorn.workers import UvicornWorker as DefaultUvicornWorker


def monkey_patch_uvicorn_server():
    """
    Monkey patch UvicornServer to handle additional unix signals with graceful shutting down

    """
    from uvicorn.main import Server
    from uvicorn.main import logger as uvicorn_logger

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

        uvicorn_logger.info(
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
        # Disable uvicorn access log for now, since newer version use INFO level log print out api-key in header...
        "access_log": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.log.info(
            f"[UvicornWorker] configure uvicorn worker limit_max_requests={self.config.limit_max_requests} "
            f"based on gunicorn configured max_requests={self.cfg.max_requests} "
            f"and max_requests_jitter={self.cfg.max_requests_jitter}"
        )
        self.log.info(
            f"[UvicornWorker] worker initialized with config={self.config.__dict__}"
        )

    async def callback_notify(self):
        await super().callback_notify()
        self.log.info(f"[UvicornWorker] (pid: {self.pid}) Heartbeat!")

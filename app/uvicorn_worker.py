from uvicorn.workers import UvicornWorker as DefaultUvicornWorker


class UvicornWorker(DefaultUvicornWorker):
    """
    Extended gunicorn worker class from uvicorn.workers.UvicornWorker to allow more flexible configurations
    """

    CONFIG_KWARGS = {"loop": "asyncio", "http": "httptools", "lifespan": "on"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_worker_max_requests()

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

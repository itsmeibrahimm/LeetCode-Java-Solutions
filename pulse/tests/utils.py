import logging
import os
import time

SERVICE_URI = os.getenv("SERVICE_URI")

logger = logging.getLogger(__name__)


def current_time_ms():
    return time.time() * 1000


def decorate_api_call(func):
    def echo_func(*args, **kwargs):
        if "_return_http_data_only" not in kwargs:
            kwargs["_return_http_data_only"] = False

        if "_preload_content" not in kwargs:
            kwargs["_preload_content"] = True

        if "_request_timeout" not in kwargs:
            kwargs["_request_timeout"] = 5  # seconds

        logger.info(f"Calling [{func.__name__}] with arguments={kwargs}")

        start = current_time_ms()
        request_id = None
        try:
            result = func(*args, **kwargs)
            elapsed = current_time_ms() - start
            request_id = (
                result[2].get("x-payment-request-id", None)
                if len(result) >= 2
                else None
            )
            logger.info(f"RequestId={request_id} Execution completed in={elapsed}ms")
            return result
        except Exception:
            elapsed = current_time_ms() - start
            logger.info(f"RequestId={request_id} Failed in={elapsed}ms")
            raise

    return echo_func

import logging
import os
import platform
import sys

import structlog
from pythonjsonlogger import jsonlogger

# see https://github.com/madzak/python-json-logger/blob/master/src/pythonjsonlogger/jsonlogger.py#L18
# for a list of supported fields and reserved attributes for logging
INCLUDED_LOG_FIELDS = "(req_id) (timestamp) (name) (message)"

is_debug = os.environ.get("ENVIRONMENT") in ("local", "testing")

_handler = logging.StreamHandler(sys.stdout)
_formatter = jsonlogger.JsonFormatter(INCLUDED_LOG_FIELDS)
_handler.setFormatter(_formatter)

_sys_logger = logging.getLogger()
_sys_logger.setLevel(logging.INFO)
if is_debug:
    _sys_logger.setLevel(logging.DEBUG)
_sys_logger.addHandler(_handler)


def add_log_level(logger: structlog.BoundLogger, log_level: str, event_dict: dict):
    """
    add the log level (as text) to the log output
    """
    event_dict["level"] = log_level.upper()
    return event_dict


def add_app_info(logger: structlog.BoundLogger, log_level: str, event_dict: dict):
    """
    application info (environment, etc)
    """
    event_dict["hostname"] = platform.node()
    event_dict["app"] = {"name": "payment-service", "env": os.environ["ENVIRONMENT"]}
    return event_dict


def add_err_info(logger: structlog.BoundLogger, log_level: str, event_dict: dict):
    """
    format exception stack traces (based on structlog.processors.format_exc_info)
    """
    exc_info: Exception = event_dict.pop("exc_info", None)
    if exc_info:
        event_dict["error"] = {
            "type": exc_info.__class__.__name__,
            "msg": str(exc_info),
        }

        if True:
            event_dict["error"]["stack"] = structlog.processors._format_exception(
                structlog.processors._figure_out_exc_info(exc_info)
            )
    return event_dict


# configure structlog globally
structlog.configure_once(
    processors=[
        # filter out messages below the current level
        structlog.stdlib.filter_by_level,
        # global
        structlog.processors.TimeStamper(fmt="iso"),
        # application info
        add_log_level,
        add_app_info,
        # allow formatting of positional args
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        # custom exception logging
        add_err_info,
        # output formatting
        structlog.processors.UnicodeDecoder(),
        # integrate with JsonLogger
        structlog.stdlib.render_to_log_kwargs,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# used for application initialization
init_logger = structlog.get_logger("initialization")
# used for general application usage
root_logger = structlog.get_logger("application")
# get or create a named logger
get_logger = structlog.get_logger

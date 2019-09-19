import logging
import datetime
import os
import platform
import sys
from typing import Callable, Dict, Optional
from typing_extensions import Protocol

import structlog
from contextvars import ContextVar
import uuid
from pythonjsonlogger import jsonlogger

REQUEST_ID: ContextVar[Optional[uuid.UUID]] = ContextVar("REQUEST_ID")

# see https://github.com/madzak/python-json-logger/blob/master/src/pythonjsonlogger/jsonlogger.py#L18
# for a list of supported fields and reserved attributes for logging
INCLUDED_LOG_FIELDS = "(name) (message)"

is_debug = os.environ.get("ENVIRONMENT") in ("local", "testing")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(
        self, log_record: Dict, record: logging.LogRecord, message_dict: Dict
    ):
        super().add_fields(log_record, record, message_dict)
        logger_add_timestamp(log_record, record, message_dict)
        logger_add_log_level(log_record, record, message_dict)
        logger_add_app_info(log_record, record, message_dict)
        logger_add_thread(log_record, record, message_dict)
        logger_add_request_id(log_record, record, message_dict)


_handler = logging.StreamHandler(sys.stdout)
_formatter = CustomJsonFormatter(INCLUDED_LOG_FIELDS)
_handler.setFormatter(_formatter)

_sys_logger = logging.getLogger()
_sys_logger.setLevel(logging.INFO)
if is_debug:
    _sys_logger.setLevel(logging.DEBUG)
if _sys_logger.hasHandlers():
    raise RuntimeError(
        f"logging is already initialized. import {__name__} earlier in the application entrypoint"
    )
_sys_logger.addHandler(_handler)


def set_request_id(uuid: uuid.UUID):
    REQUEST_ID.set(uuid)


def logger_add_timestamp(
    log_record: Dict, record: logging.LogRecord, message_dict: Dict
):
    if "timestamp" not in log_record:
        log_record["timestamp"] = (
            datetime.datetime.fromtimestamp(record.created).isoformat() + "Z"
        )


def logger_add_log_level(
    log_record: Dict, record: logging.LogRecord, message_dict: Dict
):
    if log_record.get("level"):
        log_record["level"] = log_record["level"].upper()
    else:
        log_record["level"] = record.levelname


def logger_add_app_info(
    log_record: Dict, record: logging.LogRecord, message_dict: Dict
):
    if "pid" not in log_record:
        log_record["pid"] = os.getpid()
    if "hostname" not in log_record:
        log_record["hostname"] = platform.node()
    if "app" not in log_record:
        log_record["app"] = {
            "name": "payment-service",
            "env": os.environ["ENVIRONMENT"],
        }


def logger_add_thread(log_record: Dict, record: logging.LogRecord, message_dict: Dict):
    if record.threadName != "MainThread":
        log_record["thread"] = record.threadName


def logger_add_request_id(
    log_record: Dict, record: logging.LogRecord, message_dict: Dict
):
    if "req_id" not in log_record:
        req_id = REQUEST_ID.get(None)
        if req_id:
            log_record["req_id"] = str(req_id)


def add_log_level(logger: structlog.BoundLogger, log_level: str, event_dict: dict):
    """
    add the log level (as text) to the log output
    """
    event_dict["level"] = log_level.upper()
    return event_dict


def add_app_info(logger: structlog.BoundLogger, log_level: str, event_dict: dict):
    """
    application info (pid, hostname, environment, etc)
    """
    event_dict["pid"] = os.getpid()
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


class Log(Protocol):
    """
    Helper protocol to allow BoundLoggerLazyProxy has statical type hinting
    """

    def debug(self, event=None, *args, **kw):
        pass

    def info(self, event=None, *args, **kw):
        pass

    def warning(self, event=None, *args, **kw):
        pass

    warn: Callable = warning

    def error(self, event=None, *args, **kw):
        pass

    def critical(self, event=None, *args, **kw):
        pass

    def exception(self, event=None, *args, **kw):
        pass


# used for application initialization
init_logger: Log = structlog.get_logger("initialization")
# used for general application usage
root_logger: Log = structlog.get_logger("application")
# get or create a named logger
get_logger: Callable[..., Log] = structlog.get_logger

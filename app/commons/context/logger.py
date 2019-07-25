import logging
import sys

import structlog
from pythonjsonlogger import jsonlogger

# see https://github.com/madzak/python-json-logger/blob/master/src/pythonjsonlogger/jsonlogger.py#L18
# for a list of supported fields and reserved attributes for logging
INCLUDED_LOG_FIELDS = "(message) (timestamp) (name)"

_handler = logging.StreamHandler(sys.stdout)
_formatter = jsonlogger.JsonFormatter(INCLUDED_LOG_FIELDS)
_handler.setFormatter(_formatter)

_sys_logger = logging.getLogger()
_sys_logger.setLevel(logging.INFO)
_sys_logger.addHandler(_handler)

root_logger = structlog.wrap_logger(
    logger=_sys_logger,
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.render_to_log_kwargs,
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

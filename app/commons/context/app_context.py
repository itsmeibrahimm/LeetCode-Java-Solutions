from dataclasses import dataclass
from structlog import BoundLogger

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger


@dataclass
class AppContext:
    log: BoundLogger


def get_app_context(config: AppConfig) -> AppContext:
    return AppContext(log=root_logger)

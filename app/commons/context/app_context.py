from dataclasses import dataclass
from fastapi import FastAPI
from structlog import BoundLogger
from typing import Any, cast

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger


@dataclass
class AppContext:
    log: BoundLogger


def set_context_for_app(app: FastAPI, config: AppConfig) -> AppContext:
    assert "context" not in app.extra, "app context is already set"
    context = AppContext(log=root_logger)
    context.log.debug("app context created")
    app.extra["context"] = cast(Any, context)
    return context


def get_context_from_app(app: FastAPI) -> AppContext:
    context = app.extra.get("context")
    assert isinstance(context, AppContext), "app context has correct type"
    return cast(AppContext, context)

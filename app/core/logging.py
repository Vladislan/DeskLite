# app/core/logging.py
import json
import logging
import logging.config
import uuid
from typing import Any, Mapping
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

def setup_logging(level: str = "INFO") -> None:
    """Єдина конфігурація логів для апки та Uvicorn."""
    LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {"format": LOG_FORMAT},
        },
        "handlers": {
            "default": {"class": "logging.StreamHandler", "formatter": "plain"},
        },
        "loggers": {
            "": {"handlers": ["default"], "level": level},
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": level, "propagate": False},
        },
    })

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Проброс/створення X-Request-ID для трейсингу запитів:
    - читає з вхідного заголовка (якщо є),
    - інакше генерує,
    - додає в response headers і в контекст логів (через extra).
    """

    header_name = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.header_name, str(uuid.uuid4()))
        # покладемо в state, щоб можна було дістати у роутерах/логах
        request.state.request_id = request_id

        # Прокинемо далі та додамо заголовок у відповідь
        response: Response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response

def log_extra(request: Request) -> Mapping[str, Any]:
    """
    Маленький хелпер для роутерів:
    logger.info("created", extra={"request_id": log_extra(req)["request_id"]})
    """
    rid = getattr(request.state, "request_id", None)
    return {"request_id": rid} if rid else {}

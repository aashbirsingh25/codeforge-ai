import logging
import logging.config
from typing import Any, Dict, Optional

LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "level": "INFO",
            "filename": "app.log",
            "encoding": "utf-8",
            "maxBytes": 5242880,
            "backupCount": 3
        }
    },
    "loggers": {
        "app": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    }
}

def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)

structured_logger = logging.getLogger("app.structured")

def log_structured_event(
    event: str,
    request_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    provider: Optional[str] = None,
    tool: Optional[str] = None,
    duration: Optional[float] = None,
    status: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Utility logger generating structured log trace strings for parsers.
    """
    parts = [f"event={event}"]
    if request_id:
        parts.append(f"request_id={request_id}")
    if execution_id:
        parts.append(f"execution_id={execution_id}")
    if provider:
        parts.append(f"provider={provider}")
    if tool:
        parts.append(f"tool={tool}")
    if duration is not None:
        parts.append(f"duration={duration:.4f}s")
    if status:
        parts.append(f"status={status}")
    if extra:
        for k, v in extra.items():
            parts.append(f"{k}={v}")
    structured_logger.info(" | ".join(parts))

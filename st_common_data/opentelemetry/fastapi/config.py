import sys
from typing import Any


__all__ = ("get_logging",)


def get_logging() -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,

        # FORMATTERS
        "filters": {
            "celery": {
                "()": "st_common_data.opentelemetry.logs.CeleryFilter",
            },
        },

        # FORMATTERS
        "formatters": {
            "json": {
                "()": "st_common_data.opentelemetry.logs.JsonFormatter",
            },
        },

        # HADNLERS
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout,
            },
            "celery_console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout,
                "filters": ["celery",],
            },
        },
        # LOGGERS
        "loggers": {
            "celery": {
                "handlers": ["celery_console"],
                "level": "INFO",
                "propagate": False,
            },

            "": {
                "handlers": ["console",],
                "level": "INFO",
            },
        },
    }





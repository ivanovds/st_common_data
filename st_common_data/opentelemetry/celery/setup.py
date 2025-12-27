from typing import Callable

from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from celery import signals, Celery

from .instrumentator import CustomCeleryInstrumentor

__all__ = ("setup_telemetry", )


def setup_telemetry(app: Celery, init_function: Callable[None, None]) -> None:
    app.conf.update(
        worker_hijack_root_logger=False,
    )
    signals.celeryd_init.connect(lambda **_: init_function(), weak=False)

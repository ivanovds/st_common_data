import logging
from functools import partial

from fastapi import FastAPI
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from celery import Celery

from st_common_data.opentelemetry.metrics import setup_metrics as _setup_metrics
from st_common_data.opentelemetry.celery.setup import setup_telemetry as setup_celery_telemetry
from st_common_data.opentelemetry.celery.instrumentator import CustomCeleryInstrumentor

from app.settings import config as settings


__all__ = ("setup_telemetry", "setup_celery",)

logger = logging.getLogger(__name__)

_WORKER_POSTFIX = "-worker"
_OTL_METRICS_HOST = settings.otl_metrics_host


def _setup_telemetry(service_name: str | None = None) -> None:
    resource = Resource.create({"service.name": service_name or settings.project_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=False)
    CustomCeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()

    _setup_metrics(resource, _OTL_METRICS_HOST)


def setup_telemetry(app: FastAPI, service_name: str | None = None):
    _setup_telemetry(service_name=service_name)

    FastAPIInstrumentor.instrument_app(app)


def setup_celery(app: Celery) -> None:
    setup_celery_telemetry(
        app,
        partial(
            _setup_telemetry,
            service_name=settings.project_name + _WORKER_POSTFIX,
        )
    )

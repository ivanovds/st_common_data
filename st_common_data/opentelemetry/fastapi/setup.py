import logging

from fastapi import FastAPI
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from celery import Celery

from st_common_data.opentelemetry.metrics import setup_metrics as _setup_metrics
from st_common_data.opentelemetry.celery.setup import setup_telemetry as setup_celery_telemetry

from app.settings import config as settings


__all__ = ("setup_telemetry", "setup_metrics", "setup_celery",)

logger = logging.getLogger(__name__)

_WORKER_POSTFIX = "-worker"
_OTL_METRICS_HOST = "otl_metrics_host"


def setup_telemetry(app: FastAPI, service_name: str | None = Nono):
    resource = Resource.create({"service.name": service_name or settings.project_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    LoggingInstrumentor().instrument(set_logging_format=False)
    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()


def setup_metrics() -> None:
    _setup_metrics(_OTL_METRICS_HOST)


def setup_celery(*, celery_app: Celery, fastapi_app: FastAPI) -> None:
    setup_celery_telemetry(
        celery_app,
        partial(
            setup_telemetry,
            app=fastapi_app,
            service_name=settings.PROJECT_NAME + _WORKER_POSTFIX,
        )
    )

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

from st_common_data.opentelemetry.metrics import setup_metrics as _setup_metrics

from app.settings import config as settings

logger = logging.getLogger(__name__)

__all__ = ("setup_telemetry", "setup_metrics",)


_OTL_METRICS_HOST = "otl_metrics_host"


def setup_telemetry(app: FastAPI):
    resource = Resource.create({"service.name": settings.project_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    LoggingInstrumentor().instrument(set_logging_format=False)
    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()


def setup_metrics() -> None:
    if host := getattr(settings, _OTL_METRICS_HOST, None):
        _setup_metrics(host)
    else:
        logger.warning(f"{_OTL_METRICS_HOST} is empty")


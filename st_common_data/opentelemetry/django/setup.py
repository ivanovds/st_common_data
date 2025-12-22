import logging

from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from django.conf import settings

from st_common_data.opentelemetry.metrics import setup_metrics as _setup_metrics


logger = logging.getLogger(__name__)

__all__ = ("setup_telemetry", "setup_metrics",)


_OTL_METRICS_HOST = "OTL_METRICS_HOST"


def setup_telemetry():
    resource = Resource.create({"service.name": settings.PROJECT_NAME})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=False)
    DjangoInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()


def setup_metrics() -> None:
    if host := getattr(settings, _OTL_METRICS_HOST, None):
        _setup_metrics(host)
    else:
        logger.warning(f"{_OTL_METRICS_HOST} is empty")

import logging
from functools import partial

from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from django.conf import settings
from celery import Celery

from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

from st_common_data.opentelemetry.django.http_route import (
    request_hook as _http_route_request_hook,
    response_hook as _http_route_response_hook,
)
from st_common_data.opentelemetry.semconv import apply_semconv_opt_in
from st_common_data.opentelemetry.metrics import setup_metrics as _setup_metrics
from st_common_data.opentelemetry.celery.setup import setup_telemetry as setup_celery_telemetry
from st_common_data.opentelemetry.celery.instrumentator import CustomCeleryInstrumentor


__all__ = ("setup_telemetry", "setup_celery",)

logger = logging.getLogger(__name__)

_WORKER_POSTFIX = "-worker"
_OTL_METRICS_HOST = settings.OTL_METRICS_HOST 


def setup_telemetry(service_name: str | None = None, role: str = "backend") -> None:
    apply_semconv_opt_in(
        getattr(settings, "OTEL_SEMCONV_STABILITY_OPT_IN", None)
    )

    resource = Resource.create({
        "service.name": service_name or settings.PROJECT_NAME,
        "service.role": role,
    })
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(set_logging_format=False)
    DjangoInstrumentor().instrument(
        middleware_position=1, # to be after health middleware
        request_hook=_http_route_request_hook,
        response_hook=_http_route_response_hook,
    )
    CustomCeleryInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()

    _setup_metrics(resource, _OTL_METRICS_HOST )


def setup_celery(app: Celery) -> None:
    setup_celery_telemetry(
        app,
        partial(
            setup_telemetry,
            service_name=settings.PROJECT_NAME + _WORKER_POSTFIX,
            role="worker",
        ),
    )

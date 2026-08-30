import logging

from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, resolve
from opentelemetry.instrumentation.django.middleware.otel_middleware import (
    _DjangoMiddleware,
)
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Span

__all__ = (
    "get_route_template",
    "request_hook",
    "response_hook",
)

logger = logging.getLogger(__name__)

_DURATION_ATTRS_KEY = "st_common_data.otel.duration_attrs"


def get_route_template(request: HttpRequest) -> str:
    match = getattr(request, "resolver_match", None)
    route = getattr(match, "route", None) if match is not None else None

    if not route:
        try:
            route = resolve(request.path_info).route
        except Resolver404:
            route = None
        except Exception:
            logger.exception("http.route resolution failed")
            route = None

    return route or "{unmatched}"


def request_hook(span: Span, request: HttpRequest) -> None:
    duration_attrs = request.META.get(_DjangoMiddleware._environ_duration_attr_key)
    if duration_attrs is not None:
        request.META[_DURATION_ATTRS_KEY] = duration_attrs


def response_hook(span: Span, request: HttpRequest, response: HttpResponse) -> None:
    route = get_route_template(request)

    if span.is_recording():
        span.set_attribute(SpanAttributes.HTTP_ROUTE, route)

    duration_attrs = request.META.pop(_DURATION_ATTRS_KEY, None)
    if duration_attrs is None:
        return

    duration_attrs[SpanAttributes.HTTP_ROUTE] = route
    duration_attrs[SpanAttributes.HTTP_TARGET] = route

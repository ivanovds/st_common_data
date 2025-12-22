# logging_json.py
import json
import logging
import traceback
from datetime import datetime, timezone

from opentelemetry import trace
from django.conf import settings

from st_common_data.info.base import make_project_info_dict


tracer = trace.get_tracer(__name__)


__all__ = ("JsonFormatter", "CeleryFilter",)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        info = make_project_info_dict()

        trace_id = getattr(record, "otelTraceID", 0)
        span_id = getattr(record, "otelSpanID", 0)

        trace_id = getattr(record, "customOtelTraceID", trace_id)
        span_id = getattr(record, "customOtelSpanID", span_id)

        extra = getattr(record, "extra", {})

        if exc_info := record.exc_info:
            extra["traceback"] = "".join(traceback.format_exception(*exc_info))  # type: ignore

        log = {
            "severityText": record.levelname,
            "body": record.getMessage(),
            "traceId": trace_id,
            "spanId": span_id,
            "attributes": {
                "file": record.pathname,
                "line": record.lineno,
                "func": record.funcName,
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            },
            "resource": {
                "attributes": {
                    "service.name": info["name"],
                    "service.version": info["version"],
                    "service.namespace": "backend",
                    "deployment.environment": info["environment"]
                }
            }
        }

        log["attributes"].update(extra)  # type: ignore

        return json.dumps(log, ensure_ascii=False)


class CeleryFilter(logging.Filter):
    """
    Filters celery tasks' logs without trace
    """
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        if ctx and ctx.trace_id != 0:
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")
        else:
            trace_id = None
            span_id = None

        if trace_id and span_id:
            return True

        if "received" in record.getMessage():
            return False

        return True

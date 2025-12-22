import logging

from celery import signals
from opentelemetry.propagate import extract
from opentelemetry.instrumentation.celery import CeleryInstrumentor, utils, celery_getter
from opentelemetry import trace


logger = logging.getLogger(__name__)


__all__ = ("CustomCeleryInstrumentor",)


class CustomCeleryInstrumentor(CeleryInstrumentor):
    def _instrument(self, **kwargs):
        super()._instrument(**kwargs)
        signals.task_received.connect(self._trace_received, weak=False)

    def _trace_received(self, request, **kwargs):
        request.traceparent = request.message.headers.get("traceparent")
        ctx = extract(request, getter=celery_getter)
        span = trace.get_current_span(ctx)
        span_context = span.get_span_context()

        if not span_context.is_valid:
            return

        trace_id = trace.format_trace_id(span_context.trace_id)
        span_id = trace.format_span_id(span_context.span_id)
        logger.info(
            "Task %s[%s] received",
            request.name,
            request.correlation_id,
            extra={
                "customOtelTraceID": trace_id,
                "customOtelSpanID": span_id,
            }
        )

    def _trace_prerun(self, *args, **kwargs):
        super()._trace_prerun(*args, **kwargs)

        task = utils.retrieve_task(kwargs)
        task_id = utils.retrieve_task_id(kwargs)

        logger.info(f"Task {task.name}[{task_id}] started")

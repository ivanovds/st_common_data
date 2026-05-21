import logging
import time

from celery import signals
from opentelemetry.propagate import extract
from opentelemetry.instrumentation.celery import CeleryInstrumentor, utils, celery_getter
from opentelemetry import trace, metrics


logger = logging.getLogger(__name__)


__all__ = ("CustomCeleryInstrumentor",)

class CustomCeleryInstrumentor(CeleryInstrumentor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pid = None
        self._meter = None
        self._celery_task_duration = None
        self._celery_task_counter = None

    def _get_instruments(self):
        import os
        current_pid = os.getpid()
        if self._pid != current_pid:
            self._meter = metrics.get_meter(__name__)
            self._celery_task_duration = self._meter.create_histogram(
                name="celery_task_duration",
                description="Duration of Celery tasks in seconds",
                unit="s",
            )
            self._celery_task_counter = self._meter.create_counter(
                name="celery_task_executions_count",
                description="Number of times a Celery task was executed",
            )
            self._pid = current_pid
        return self._celery_task_duration, self._celery_task_counter

    def _instrument(self, **kwargs):
        super()._instrument(**kwargs)
        
        signals.task_received.connect(self._trace_received, weak=False)
        signals.task_prerun.connect(self._metric_start_timer, weak=False)
        signals.task_postrun.connect(self._metric_record_results, weak=False)
    
    def _metric_start_timer(self, task_id, task, *args, **kwargs):
        """Save the start time when the task begins."""
        task.request.otel_start_time = time.time()
        
    def _metric_record_results(self, task_id, task, *args, **kwargs):
        """Calculate duration and increment count when the task finishes."""
        state = kwargs.get('state', 'UNKNOWN')
        attributes = {
            "task_name": task.name,
            "status": state
        }
        
        duration_instrument, counter_instrument = self._get_instruments()
        
        counter_instrument.add(1, attributes=attributes)
        logger.info("Task %s[%s] executed with status %s", task.name, task_id, state)
        
        start_time = getattr(task.request, 'otel_start_time', None)
        if start_time:
            duration = time.time() - start_time
            duration_instrument.record(duration, attributes=attributes)
            logger.info("Metrics for task %s (status: %s, duration: %.4fs) recorded to OpenTelemetry", task.name, state, duration)
        
        # DEBUG: Let's inspect the active MeterProvider and FORCE it to flush immediately
        provider = metrics.get_meter_provider()
        logger.info(f"[DEBUG] Active MeterProvider is: {provider.__class__.__name__}")
        if hasattr(provider, "force_flush"):
            logger.info("[DEBUG] Forcing metric flush to console and collector...")
            provider.force_flush()
        else:
            logger.warning("[DEBUG] Provider does not have force_flush! (Is it a NoOpMeterProvider?)")

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

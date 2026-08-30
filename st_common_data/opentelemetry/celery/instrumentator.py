import logging
import time

from celery import signals
from opentelemetry.propagate import extract
from opentelemetry.instrumentation.celery import CeleryInstrumentor, utils, celery_getter
from opentelemetry import trace, metrics


logger = logging.getLogger(__name__)


__all__ = ("CustomCeleryInstrumentor",)

_PUBLISHED_AT_HEADER = "otel_published_at"

class CustomCeleryInstrumentor(CeleryInstrumentor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pid = None
        self._meter = None
        self._celery_task_duration = None
        self._celery_task_counter = None
        self._celery_task_active = None
        self._celery_task_objects = None
        self._celery_task_partial_failures = None
        self._celery_task_queue_wait = None
        self._last_flush = 0.0

    def _ensure_instruments(self):
        import os
        current_pid = os.getpid()
        if self._pid == current_pid:
            return

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
        self._celery_task_active = self._meter.create_up_down_counter(
            name="celery_task_active",
            description="Number of Celery tasks currently running",
        )
        self._celery_task_objects = self._meter.create_counter(
            name="celery_task_objects_created",
            description="Number of objects a Celery task reported as created",
        )
        self._celery_task_partial_failures = self._meter.create_counter(
            name="celery_task_partial_failures",
            description="Number of Celery tasks that succeeded while reporting errors",
        )
        self._celery_task_queue_wait = self._meter.create_histogram(
            name="celery_task_queue_wait",
            description="Seconds a Celery task waited in the queue before starting",
            unit="s",
        )
        self._last_flush = 0.0
        self._pid = current_pid

    @staticmethod
    def _has_reported_errors(retval):
        """Detect a task that finished successfully but reported errors of its own."""
        return isinstance(retval, dict) and bool(retval.get("errors"))

    @staticmethod
    def _extract_objects_created(retval):
        """Read the objects_created convention from a task result, if present."""
        if not isinstance(retval, dict):
            return None

        value = retval.get("objects_created")
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if value < 0:
            return None

        return value

    def _instrument(self, **kwargs):
        super()._instrument(**kwargs)
        
        signals.before_task_publish.connect(self._stamp_published_at, weak=False)
        signals.task_received.connect(self._trace_received, weak=False)
        signals.task_prerun.connect(self._metric_start_timer, weak=False)
        signals.task_postrun.connect(self._metric_record_results, weak=False)
    
    def _stamp_published_at(self, headers=None, **kwargs):
        """Stamp the publish time so the worker can measure how long the task queued."""
        if isinstance(headers, dict):
            headers[_PUBLISHED_AT_HEADER] = time.time()

    def _metric_start_timer(self, task_id, task, *args, **kwargs):
        """Save the start time, mark the task as running, record its queue wait."""
        now = time.time()
        task.request.otel_start_time = now

        self._ensure_instruments()
        self._celery_task_active.add(1, attributes={"task_name": task.name})

        published_at = getattr(task.request, _PUBLISHED_AT_HEADER, None)
        scheduled = getattr(task.request, "eta", None)
        if isinstance(published_at, (int, float)) and not scheduled:
            self._celery_task_queue_wait.record(
                max(now - published_at, 0.0),
                attributes={"task_name": task.name},
            )
        
    def _metric_record_results(self, task_id, task, *args, **kwargs):
        """Calculate duration and increment count when the task finishes."""
        state = kwargs.get('state', 'UNKNOWN')
        attributes = {
            "task_name": task.name,
            "status": state
        }
        
        self._ensure_instruments()
        retval = kwargs.get("retval")

        self._celery_task_active.add(-1, attributes={"task_name": task.name})
        self._celery_task_counter.add(1, attributes=attributes)

        objects_created = self._extract_objects_created(retval)
        if objects_created is not None:
            self._celery_task_objects.add(
                objects_created, attributes={"task_name": task.name}
            )

        if self._has_reported_errors(retval):
            self._celery_task_partial_failures.add(
                1, attributes={"task_name": task.name}
            )
        logger.info("Task %s[%s] executed with status %s", task.name, task_id, state)
        
        start_time = getattr(task.request, 'otel_start_time', None)
        if start_time:
            duration = time.time() - start_time
            self._celery_task_duration.record(duration, attributes=attributes)
            logger.info("Metrics for task %s (status: %s, duration: %.4fs) recorded to OpenTelemetry", task.name, state, duration)
        
        now = time.time()
        if now - self._last_flush >= 10:
            provider = metrics.get_meter_provider()
            if hasattr(provider, "force_flush"):
                provider.force_flush()
            self._last_flush = now


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

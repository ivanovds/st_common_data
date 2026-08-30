import logging

from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import DropAggregation, View


__all__ = ("setup_metrics",)

logger = logging.getLogger(__name__)


def setup_metrics(resource: Resource, metrics_collector_host: str | None = None) -> None:
    if not metrics_collector_host:
        logger.warning("metrics_collector_host is empty")
        return

    exporter = OTLPMetricExporter(endpoint=metrics_collector_host, insecure=True)
    
    # Lower export interval to 10 seconds (default is 60s) to see if the thread is alive
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
    
    provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
        views=[
            View(
                instrument_name="flower.task.runtime.seconds",
                aggregation=DropAggregation(),
            ),
        ],
    )
    
    # -------------------------------------------------------------
    # CRITICAL FIX FOR MULTIPROCESSING (CELERY/GUNICORN)
    # OpenTelemetry blocks `set_meter_provider` from being called twice.
    # When a parent process sets it, it gets locked. When child processes fork,
    # they inherit the locked provider (with dead threads) and OpenTelemetry silently
    # ignores the child's attempt to setup a new provider.
    # We must forcefully unlock it here before setting the new one!
    # -------------------------------------------------------------
    from opentelemetry import metrics as otel_metrics
    if hasattr(otel_metrics, "_METER_PROVIDER_SET_ONCE"):
        otel_metrics._METER_PROVIDER_SET_ONCE._is_set = False
    otel_metrics._METER_PROVIDER = None
    
    set_meter_provider(provider)
    logger.info(f"Setting grpc metrics for {metrics_collector_host}")

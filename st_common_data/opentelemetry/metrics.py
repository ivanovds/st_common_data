import logging

from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


__all__ = ("setup_metrics",)

logger = logging.getLogger(__name__)


def setup_metrics(resource: Resource, metrics_collector_host: str | None = None) -> None:
    if not metrics_collector_host:
        logger.warning("metrics_collector_host is empty")
        return

    exporter = OTLPMetricExporter(endpoint=metrics_collector_host, insecure=True)
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    set_meter_provider(provider)
    logger.info(f"Setting grpc metrics for {metrics_collector_host}")

import logging

from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


__all__ = ("setup_metrics",)

logger = logging.getLogger(__name__)


def setup_metrics(metrics_collector_host: str | None = None) -> None:
    if not metrics_collector_host:
        logger.warning("metrics_collector_host is empty")
        return

    exporter = OTLPMetricExporter(endpoint=f"{metrics_collector_host}/v1/metrics")
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(metric_readers=[reader])
    set_meter_provider(provider)

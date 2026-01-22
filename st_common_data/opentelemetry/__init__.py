import sys
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.metrics import set_meter_provider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor


__all__ = ('SpanLoggingHandler', 'OpenTelemetryHandler')


class SpanLoggingHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)
        self.tracer = trace.get_tracer(__name__)

    def emit(self, record):
        super().emit(record)
        with self.tracer.start_as_current_span(f"log {record.levelname}") as span:
            span.add_event(
                name=f"log {record.levelname}",
                attributes={
                    "log.level": record.levelname,
                    "log.message": record.getMessage(),
                    "logger.name": record.name,
                    "file": record.pathname,
                    "line": record.lineno,
                }
            )


class OpenTelemetryHandler:
    def __init__(self, service_name: str, collector_trace_host: str, collector_metrics_host: str):
        self.service_name = service_name
        self.collector_trace_host = collector_trace_host
        self.collector_metrics_host = collector_metrics_host
        self.active_tracing = False

    def general_set_up(self, is_raw_postgres: bool = True):
        if self.collector_trace_host:
            self.set_up_traces()
        if self.collector_metrics_host:
            self.set_up_metrics()

        if self.active_tracing:
            RequestsInstrumentor().instrument()
            if is_raw_postgres:
                Psycopg2Instrumentor().instrument()

    def set_up_traces(self):
        resource = Resource(attributes={"service.name": self.service_name})
        trace_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=f"{self.collector_trace_host}v1/traces")
        span_processor = BatchSpanProcessor(span_exporter)
        trace_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(trace_provider)
        self.active_tracing = True

    def set_up_metrics(self):
        exporter = OTLPMetricExporter(endpoint=f"{self.collector_metrics_host}v1/metrics")
        reader = PeriodicExportingMetricReader(exporter)
        provider = MeterProvider(metric_readers=[reader])
        set_meter_provider(provider)

    def set_up_django(self):
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        if self.active_tracing:
            DjangoInstrumentor().instrument()

    def set_up_celery(self):
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        if self.active_tracing:
            CeleryInstrumentor().instrument()

    def set_up_fastapi(self, app):
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        if self.active_tracing:
            FastAPIInstrumentor().instrument_app(app)

    def set_up_grpc_client(self):
        from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer
        if self.active_tracing:
            GrpcAioInstrumentorServer().instrument()

    def set_up_grpc_server(self):
        from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorClient
        if self.active_tracing:
            GrpcAioInstrumentorClient().instrument()

    def set_up_sqlalchemy(self, engine):
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        if self.active_tracing:
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                enable_commenter=True,
                commenter_options={"db_driver": True}
            )

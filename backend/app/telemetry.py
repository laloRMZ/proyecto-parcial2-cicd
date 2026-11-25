import json
import logging
import os
import time
from typing import Dict

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _parse_otlp_headers(raw_headers: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if not raw_headers:
        return headers
    for pair in raw_headers.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers


def setup_telemetry(service_name: str = "proyecto2-app"):
    logger = logging.getLogger("proyecto2")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip().rstrip("/")
    headers = _parse_otlp_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "deployment.environment": os.getenv("APP_ENV", "production"),
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    meter_provider = MeterProvider(resource=resource)

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

        span_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

        metric_exporter = OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])

        log_exporter = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter("proyecto2.http")
    request_counter = meter.create_counter(
        name="http_requests_total",
        description="Total HTTP requests by endpoint and statusCode",
        unit="1",
    )
    error_counter = meter.create_counter(
        name="http_errors_total",
        description="Total HTTP error responses (4xx/5xx)",
        unit="1",
    )
    latency_histogram = meter.create_histogram(
        name="http_request_duration_ms",
        description="HTTP request latency in milliseconds",
        unit="ms",
    )

    return {
        "logger": logger,
        "tracer": trace.get_tracer("proyecto2.app"),
        "request_counter": request_counter,
        "error_counter": error_counter,
        "latency_histogram": latency_histogram,
    }

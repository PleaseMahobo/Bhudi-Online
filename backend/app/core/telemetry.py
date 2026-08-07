"""OpenTelemetry tracing for Bhudi Online.

Enabled when OTEL_ENABLED=true (or OTEL_EXPORTER_OTLP_ENDPOINT is set).
Missing optional packages degrade to a no-op so local/dev stays lightweight.

Env:
  OTEL_ENABLED                 true/false (default: false unless endpoint set)
  OTEL_SERVICE_NAME            default bhudi-api
  OTEL_SERVICE_VERSION         default 1.0.0
  OTEL_ENVIRONMENT             default development
  OTEL_EXPORTER_OTLP_ENDPOINT  e.g. http://otel-collector:4317 or :4318
  OTEL_EXPORTER_OTLP_PROTOCOL  grpc | http/protobuf (default grpc)
  OTEL_TRACES_SAMPLER          parentbased_always_on | always_on | always_off | traceidratio
  OTEL_TRACES_SAMPLER_ARG      ratio for traceidratio (default 1.0)
  OTEL_CONSOLE_EXPORTER        true to also log spans to stdout
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("bhudi.telemetry")

_initialized = False
_tracer = None


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def tracing_enabled() -> bool:
    if _env_bool("OTEL_ENABLED", False):
        return True
    # Auto-enable when an endpoint is configured (compose / k8s)
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def get_tracer(name: str = "bhudi"):
    """Return a tracer; no-op proxy if OTel is unavailable."""
    global _tracer
    if _tracer is not None:
        return _tracer
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except Exception:
        return _NoopTracer()


class _NoopSpan:
    def set_attribute(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        return None

    def record_exception(self, *args: Any, **kwargs: Any) -> None:
        return None

    def add_event(self, *args: Any, **kwargs: Any) -> None:
        return None

    def end(self, *args: Any, **kwargs: Any) -> None:
        return None

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


class _NoopTracer:
    def start_as_current_span(self, name: str, **kwargs: Any):
        return _NoopSpan()

    def start_span(self, name: str, **kwargs: Any):
        return _NoopSpan()


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """Convenience context manager for manual spans."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as sp:
        for k, v in attributes.items():
            try:
                sp.set_attribute(k, v)
            except Exception:
                pass
        yield sp


def setup_tracing(app: Any | None = None) -> bool:
    """
    Configure TracerProvider + OTLP exporter and instrument FastAPI/SQLAlchemy.

    Returns True if tracing was activated.
    """
    global _initialized, _tracer

    if _initialized:
        return True

    if not tracing_enabled():
        logger.info("OpenTelemetry tracing disabled")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.trace.sampling import (
            ALWAYS_OFF,
            ALWAYS_ON,
            ParentBased,
            TraceIdRatioBased,
        )
    except ImportError as e:
        logger.warning(
            "OpenTelemetry SDK not installed (%s). "
            "pip install opentelemetry-sdk opentelemetry-exporter-otlp",
            e,
        )
        return False

    service_name = os.getenv("OTEL_SERVICE_NAME", "bhudi-api")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    environment = os.getenv("OTEL_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )

    sampler_name = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_always_on").lower()
    sampler_arg = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
    if sampler_name in ("always_off", "off"):
        sampler = ALWAYS_OFF
    elif sampler_name in ("always_on", "on"):
        sampler = ALWAYS_ON
    elif sampler_name in ("traceidratio", "ratio"):
        sampler = ParentBased(TraceIdRatioBased(sampler_arg))
    else:
        sampler = ParentBased(ALWAYS_ON)

    provider = TracerProvider(resource=resource, sampler=sampler)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()

    if endpoint:
        try:
            if protocol in ("http/protobuf", "http", "http/json"):
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                # http exporter expects full traces path sometimes
                exp_endpoint = endpoint
                if not exp_endpoint.rstrip("/").endswith("v1/traces"):
                    exp_endpoint = exp_endpoint.rstrip("/") + "/v1/traces"
                exporter = OTLPSpanExporter(endpoint=exp_endpoint)
            else:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                # grpc prefers host:port without scheme in some versions; pass as-is
                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP span exporter → %s (%s)", endpoint, protocol)
        except Exception as e:
            logger.warning("OTLP exporter setup failed: %s", e)

    if _env_bool("OTEL_CONSOLE_EXPORTER", False):
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter enabled")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("bhudi", service_version)

    if app is not None:
        _instrument_fastapi(app)
    _instrument_sqlalchemy()
    _instrument_requests()

    _initialized = True
    logger.info(
        "OpenTelemetry tracing active (service=%s env=%s)", service_name, environment
    )
    return True


def _instrument_fastapi(app: Any) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,metrics,docs,redoc,openapi.json",
        )
        logger.info("FastAPI instrumented")
    except Exception as e:
        logger.warning("FastAPI instrumentation skipped: %s", e)


def _instrument_sqlalchemy() -> None:
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        from app.database.session import engine

        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumented")
    except Exception as e:
        logger.warning("SQLAlchemy instrumentation skipped: %s", e)


def _instrument_requests() -> None:
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
        logger.info("requests instrumented")
    except Exception as e:
        logger.debug("requests instrumentation skipped: %s", e)
    try:
        from opentelemetry.instrumentation.urllib import URLLibInstrumentor

        URLLibInstrumentor().instrument()
        logger.info("urllib instrumented")
    except Exception as e:
        logger.debug("urllib instrumentation skipped: %s", e)


def shutdown_tracing() -> None:
    """Flush and shutdown the tracer provider."""
    global _initialized, _tracer
    if not _initialized:
        return
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush(timeout_millis=5000)
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    except Exception as e:
        logger.warning("Tracing shutdown error: %s", e)
    _initialized = False
    _tracer = None

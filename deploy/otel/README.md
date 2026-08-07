# OpenTelemetry tracing (Bhudi API)

## Enable

```bash
export OTEL_ENABLED=true
export OTEL_SERVICE_NAME=bhudi-api
export OTEL_ENVIRONMENT=development
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc   # or http/protobuf → :4318
# optional debug:
export OTEL_CONSOLE_EXPORTER=true
```

With Docker Compose, the API is pre-wired to `http://otel-collector:4317`.

## What is instrumented

| Layer | Package |
|-------|---------|
| FastAPI HTTP routes | `opentelemetry-instrumentation-fastapi` |
| SQLAlchemy | `opentelemetry-instrumentation-sqlalchemy` |
| `requests` / `urllib` outbound | respective instrumentors |
| Manual spans | `from app.core.telemetry import span` |

Health, metrics, and OpenAPI paths are excluded from HTTP spans.

## Manual span example

```python
from app.core.telemetry import span

with span("psa.push_ticket", provider="zendesk", ticket_id=str(ticket_id)):
    ...
```

## Collector

`deploy/otel/otel-collector-config.yaml` receives OTLP on **4317 (gRPC)** and **4318 (HTTP)** and exports traces/metrics to logging (and Prometheus metrics on 8889).

Swap the logging exporter for Jaeger, Tempo, or Honeycomb in production.

## Install deps

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-sqlalchemy \
  opentelemetry-instrumentation-requests \
  opentelemetry-instrumentation-urllib
```

If packages are missing, the API still starts; tracing stays inactive.

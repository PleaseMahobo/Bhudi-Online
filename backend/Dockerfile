FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# WebSocket memory / protocol defaults (overridable at runtime)
# - WS_MAX_SIZE: 1 MiB is enough for alert batches (default uvicorn is 16 MiB)
# - WS_MAX_QUEUE: smaller inbound queue = less RAM under backpressure
# - WS_PER_MESSAGE_DEFLATE: set false under very high concurrent socket counts
ENV WS_MAX_SIZE=1048576
ENV WS_MAX_QUEUE=16
ENV WS_PING_INTERVAL=20
ENV WS_PING_TIMEOUT=20
ENV WS_PER_MESSAGE_DEFLATE=true

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Production-tuned WebSocket settings for Alert Engine / agent sockets
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --ws websockets --ws-max-size ${WS_MAX_SIZE} --ws-max-queue ${WS_MAX_QUEUE} --ws-ping-interval ${WS_PING_INTERVAL} --ws-ping-timeout ${WS_PING_TIMEOUT} --ws-per-message-deflate ${WS_PER_MESSAGE_DEFLATE}"]

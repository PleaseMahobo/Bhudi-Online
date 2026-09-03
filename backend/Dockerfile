FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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

# Force shell, Python and Uvicorn diagnostics into Railway logs.
CMD ["sh", "-c", "set -eux; echo '[startup] launching Bhudi API'; echo \"[startup] PORT=$${PORT:-8000}\"; python -u -c 'import app.main; print(\"[startup] app import succeeded\")'; echo '[startup] starting uvicorn'; exec python -u -m uvicorn app.main:app --host 0.0.0.0 --port $${PORT:-8000} --log-level debug --ws websockets --ws-max-size $${WS_MAX_SIZE} --ws-max-queue $${WS_MAX_QUEUE} --ws-ping-interval $${WS_PING_INTERVAL} --ws-ping-timeout $${WS_PING_TIMEOUT} --ws-per-message-deflate $${WS_PER_MESSAGE_DEFLATE} 2>&1"]

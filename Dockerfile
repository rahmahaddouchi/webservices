FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000 \
    APP_MODULE=app \
    LOG_DIR=/app/logs \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["sh", "-c", "mkdir -p /app/logs && flask --app ${APP_MODULE} run --host 0.0.0.0 --port ${PORT} 2>&1 | tee -a /app/logs/server.log"]
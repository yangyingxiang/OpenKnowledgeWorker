# Build from the repository root:  docker build -f backend/Dockerfile .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOMAIN_PACKS_DIR=/app/examples \
    UPLOAD_DIR=/data/uploads

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY examples/ /app/examples/

RUN useradd --create-home --uid 1000 okw && mkdir -p /data/uploads && chown -R okw /data /app
USER okw

EXPOSE 5003

# One worker process: background-job event buffers live in process memory (see app/jobs.py).
CMD ["sh", "-c", "alembic upgrade head && python seed.py --if-empty && exec gunicorn -w 1 -k gthread --threads 16 --timeout 0 -b 0.0.0.0:5003 'app:create_app()'"]

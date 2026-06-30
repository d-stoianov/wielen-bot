# Single image that supports both fetchers. The Playwright browser is only used
# when FETCHER=playwright; with FETCHER=apify it sits unused but harmless.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY pyproject.toml ./
COPY src/ ./src/

# Persisted dedup state lives here; mount a volume so it survives restarts.
RUN mkdir -p /app/data
ENV PYTHONPATH=/app/src \
    DB_PATH=/app/data/seen.sqlite3 \
    CONFIG_PATH=/app/config.yaml

CMD ["python", "-m", "wielenbot.main"]

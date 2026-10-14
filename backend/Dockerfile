# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip wheel --wheel-dir /wheels --requirement requirements.txt


FROM python:3.11-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_DATA_DIR=/tmp/ai-pdf-reader \
    PORT=10000

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates libasound2 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --shell /bin/sh app

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels --requirement requirements.txt \
    && python -c "import spacy; spacy.load('en_core_web_sm')" \
    && rm -rf /wheels

COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/setup_credentials.py ./setup_credentials.py
RUN mkdir -p /tmp/ai-pdf-reader && chown -R app:app /tmp/ai-pdf-reader /app

USER app

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '10000') + '/healthz', timeout=3)" || exit 1

CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]

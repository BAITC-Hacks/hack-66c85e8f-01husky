FROM python:3.12-slim-bookworm AS backend

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg libreoffice fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pipeline/ /app/pipeline/
COPY bots/ /app/bots/
COPY backend/ /app/backend/
WORKDIR /app/backend
RUN uv sync --locked --no-dev --project /app/backend

EXPOSE 8000

FROM backend AS bot-runtime

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    DISPLAY=:99 \
    XDG_RUNTIME_DIR=/tmp/kenes-runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends pulseaudio pulseaudio-utils xvfb \
    && uv run --no-sync --project /app/backend playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 bot \
    && mkdir -p /app/backend/data /app/backend/outbox \
    && chown -R bot:bot /app/backend/data /app/backend/outbox /opt/playwright

COPY --chmod=755 bots/entrypoint.sh /usr/local/bin/kenes-bot-entrypoint
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
USER bot
ENTRYPOINT ["kenes-bot-entrypoint"]
CMD ["uv", "run", "--no-sync", "celery", "-A", "app.tasks.celery_app:celery_app", "worker", "-Q", "bots", "--concurrency=1", "--prefetch-multiplier=1", "--loglevel=info"]

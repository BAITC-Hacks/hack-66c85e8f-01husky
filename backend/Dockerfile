FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libreoffice fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pipeline/ /app/pipeline/
COPY backend/ /app/backend/
WORKDIR /app/backend
RUN uv sync --no-dev --project /app/backend

EXPOSE 8000

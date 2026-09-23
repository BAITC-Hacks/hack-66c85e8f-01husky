# backend

```bash
cd backend
cp ../.env.example ../.env     # once
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
uv run celery -A app.tasks.celery_app worker -l info
uv run pytest
```

OpenAPI: http://localhost:8000/docs

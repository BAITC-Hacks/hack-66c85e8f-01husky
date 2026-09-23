from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, directions, meetings, participants, tasks

settings = get_settings()
app = FastAPI(title=settings.app_name, docs_url="/docs", openapi_url="/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "pipeline_fake": settings.pipeline_fake}


# Routers: add to the import above and include here. Keep alphabetical.
api.include_router(auth.router)
api.include_router(directions.router)
api.include_router(meetings.router)
api.include_router(participants.router)
api.include_router(tasks.router)

app.include_router(api)

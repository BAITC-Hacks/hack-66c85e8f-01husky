from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import (
    admin,
    auth,
    directions,
    exports,
    meetings,
    notifications,
    participants,
    tasks,
)

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


@app.middleware("http")
async def admin_no_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/admin"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@api.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "pipeline_fake": settings.pipeline_fake}


# Routers: add to the import above and include here. Keep alphabetical.
api.include_router(admin.router)
api.include_router(auth.router)
api.include_router(directions.router)
api.include_router(exports.router)
api.include_router(meetings.router)
api.include_router(notifications.router)
api.include_router(participants.router)
api.include_router(tasks.router)

app.include_router(api)
app.include_router(admin.pages)
app.mount("/admin-assets", StaticFiles(directory=admin.ASSETS), name="admin-assets")

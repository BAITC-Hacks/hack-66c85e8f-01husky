from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "protocol",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.process_meeting", "app.tasks.reminders", "app.tasks.run_bot"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Almaty",
    enable_utc=True,
    task_track_started=True,
    task_routes={"app.tasks.run_bot.run_bot": {"queue": "bots"}},
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "check-deadlines-hourly": {
            "task": "app.tasks.reminders.check_deadlines",
            "schedule": 3600.0,
        },
    },
)

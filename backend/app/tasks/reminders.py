"""Celery beat task: due_soon / overdue notifications. Owner: B5."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.reminders.check_deadlines")
def check_deadlines() -> None:
    raise NotImplementedError("B5 pending")

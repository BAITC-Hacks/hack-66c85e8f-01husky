"""Celery task: run the pipeline on a meeting and persist MeetingResult. Owner: A6."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.process_meeting.process_meeting", bind=True)
def process_meeting(self, meeting_id: int) -> None:
    raise NotImplementedError("A6 pending")

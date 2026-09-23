"""Hand a meeting to the Celery worker. CELERY_EAGER=1 (tests, no Redis) runs it inline."""

import os


def enqueue_processing(meeting_id: int) -> None:
    from app.tasks.process_meeting import process_meeting

    if os.getenv("CELERY_EAGER", "0") in {"1", "true"}:
        process_meeting.apply(args=(meeting_id,))
    else:
        process_meeting.delay(meeting_id)

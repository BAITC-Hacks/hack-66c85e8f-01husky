"""Celery task: run the pipeline on a meeting and persist MeetingResult (spec section 7)."""

import logging

import pipeline
from pipeline.models import MeetingResult
from pipeline.models import Participant as PParticipant
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Direction, Meeting, Participant, Segment, SpeakerMap, Task
from app.models.enums import MeetingStatus, SpeakerSource, TaskStatus, Urgency
from app.services.guests import resolve_guests
from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


def _set_progress(meeting_id: int, stage: str, pct: float) -> None:
    with SessionLocal() as db:
        m = db.get(Meeting, meeting_id)
        if m:
            m.progress_stage, m.progress_pct = stage, round(pct * 100, 1)
            db.commit()


def persist_result(db, m: Meeting, result: MeetingResult) -> None:
    resolve_guests(db, m, result)
    m.segments.clear()
    m.speaker_map.clear()
    m.tasks.clear()
    db.flush()

    m.segments = [
        Segment(idx=i, start=s.start, end=s.end, speaker=s.speaker, text=s.text, lang=s.lang)
        for i, s in enumerate(result.segments)
    ]
    m.speaker_map = [
        SpeakerMap(
            speaker=sm.speaker,
            participant_id=sm.participant_id,
            source=SpeakerSource(sm.source),
            confidence=sm.confidence,
        )
        for sm in result.speaker_map
    ]
    dir_by_name = {d.name: d.id for d in db.scalars(select(Direction))}
    m.tasks = [
        Task(
            assignee_participant_id=t.assignee_participant_id,
            assignee_name=t.assignee_name,
            text=t.text,
            deadline=t.deadline,
            deadline_raw=t.deadline_raw,
            urgency=Urgency(t.urgency),
            direction_id=dir_by_name.get(t.direction) or dir_by_name.get("Другое"),
            quote=t.quote,
            segment_idx=t.segment_index,
            confidence=t.confidence,
            status=TaskStatus.draft,
        )
        for t in result.tasks
    ]
    m.summary = result.summary
    m.language_stats = result.language_stats
    m.model_info = result.model_info
    if result.duration_sec:
        m.duration_sec = result.duration_sec


@celery_app.task(name="app.tasks.process_meeting.process_meeting", bind=True)
def process_meeting(self, meeting_id: int) -> None:
    with SessionLocal() as db:
        m = db.get(Meeting, meeting_id)
        if not m or not m.audio_path:
            log.warning("process_meeting: meeting %s missing or has no audio", meeting_id)
            return
        m.status, m.error, m.progress_stage, m.progress_pct = (
            MeetingStatus.processing,
            None,
            "queued",
            0.0,
        )
        db.commit()
        audio_path, meeting_date, output_language = (
            m.audio_path,
            m.meeting_date,
            m.output_language.value,
        )
        participants = m.participants or list(db.scalars(select(Participant)))
        p_participants = [
            PParticipant(id=p.id, name=p.name, role=p.position, voice_embedding=p.voice_embedding)
            for p in participants
        ]
        directions = [
            d.name for d in db.scalars(select(Direction).where(Direction.is_active.is_(True)))
        ]

    try:
        result = pipeline.process(
            audio_path,
            meeting_date,
            p_participants,
            directions,
            output_language,
            lambda stage, pct: _set_progress(meeting_id, stage, pct),
        )
        with SessionLocal() as db:
            m = db.get(Meeting, meeting_id)
            if m is None:
                log.info("process_meeting: meeting %s was deleted", meeting_id)
                return
            persist_result(db, m, result)
            m.status, m.progress_stage, m.progress_pct = MeetingStatus.draft, "done", 100.0
            db.commit()
    except Exception as e:  # noqa: BLE001
        log.error("process_meeting %s failed (%s)", meeting_id, type(e).__name__)
        # The failed persistence session has closed and rolled back before this write.
        with SessionLocal() as db:
            m = db.get(Meeting, meeting_id)
            if m is not None:
                m.status, m.error = (
                    MeetingStatus.failed,
                    f"{type(e).__name__}: processing failed; check local model and audio configuration",
                )
                db.commit()

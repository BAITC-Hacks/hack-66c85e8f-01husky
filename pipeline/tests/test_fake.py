from datetime import date

import pytest

from pipeline import fake
from pipeline.models import MeetingResult, Participant

PARTICIPANTS = [
    Participant(id=1, name="Серик Нурланов", role="Директор"),
    Participant(id=2, name="Айбек Сериков", role="Финансист"),
    Participant(id=3, name="Дана Ахметова", role="Юрист"),
]
DIRECTIONS = ["Финансы", "Кадры", "ИТ", "Юридическое", "Другое"]


@pytest.fixture
def result() -> MeetingResult:
    return fake.process("x.wav", date(2026, 9, 23), PARTICIPANTS, DIRECTIONS)


def test_shape(result: MeetingResult) -> None:
    assert len(result.segments) >= 6
    assert {m.speaker for m in result.speaker_map} == {"SPEAKER_00", "SPEAKER_01", "SPEAKER_02"}
    assert len(result.tasks) == 4
    assert result.duration_sec > 0
    assert abs(sum(result.language_stats.values()) - 1.0) < 0.05
    assert {"ru", "kk", "mixed"} <= set(result.language_stats)


def test_quotes_are_verbatim(result: MeetingResult) -> None:
    for t in result.tasks:
        assert t.quote in result.segments[t.segment_index].text


def test_assignees_resolved(result: MeetingResult) -> None:
    by_name = {t.assignee_name: t.assignee_participant_id for t in result.tasks}
    assert by_name["Айбек"] == 2
    assert by_name["Дана"] == 3


def test_deadlines_relative_to_meeting_date(result: MeetingResult) -> None:
    deadlines = {t.deadline_raw: t.deadline for t in result.tasks}
    assert deadlines["до пятницы"] == date(2026, 9, 25)
    assert deadlines["конец месяца"] == date(2026, 9, 30)
    assert deadlines["бүгін"] == date(2026, 9, 23)


def test_directions_from_input(result: MeetingResult) -> None:
    assert all(t.direction in DIRECTIONS for t in result.tasks)


def test_unknown_participants_leave_none() -> None:
    r = fake.process("x.wav", date(2026, 9, 23), [], DIRECTIONS)
    assert all(t.assignee_participant_id is None for t in r.tasks)
    assert all(m.participant_id is None for m in r.speaker_map)


def test_progress_and_kk_summary() -> None:
    stages: list[str] = []
    r = fake.process(
        "x.wav", date(2026, 9, 23), PARTICIPANTS, DIRECTIONS, "kk", lambda s, p: stages.append(s)
    )
    assert stages == ["stt", "diarize", "voiceprint", "extract", "summary"]
    assert r.summary.startswith("## Тақырып")


def test_enroll_voice_deterministic() -> None:
    a, b = fake.enroll_voice("a.wav"), fake.enroll_voice("a.wav")
    assert a == b and len(a) == 192


def test_env_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    import pipeline

    monkeypatch.setenv("PIPELINE_FAKE", "1")
    r = pipeline.process("x.wav", date(2026, 9, 23), PARTICIPANTS, DIRECTIONS)
    assert r.model_info["stt"] == "fake"
    monkeypatch.setenv("PIPELINE_FAKE", "0")
    with pytest.raises(FileNotFoundError):
        pipeline.process("x.wav", date(2026, 9, 23), PARTICIPANTS, DIRECTIONS)

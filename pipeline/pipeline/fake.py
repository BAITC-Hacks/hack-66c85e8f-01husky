"""Deterministic stand-in for the real pipeline. Enabled with PIPELINE_FAKE=1."""

from datetime import date, timedelta

from pipeline.models import (
    MeetingResult,
    OutputLanguage,
    Participant,
    ProgressCallback,
    Segment,
    SpeakerMapping,
    Task,
)

_STAGES = ("stt", "diarize", "voiceprint", "extract", "summary")

_SEGMENTS: list[tuple[float, float, str, str, str]] = [
    (
        0.0,
        6.2,
        "SPEAKER_00",
        "Коллеги, начинаем. Сегодня обсуждаем бюджет на четвёртый квартал и запуск нового склада.",
        "ru",
    ),
    (
        6.4,
        13.9,
        "SPEAKER_01",
        "Қаржы бойынша есеп дайын, бірақ бірнеше сұрақ бар. Смета әлі бекітілмеген.",
        "kk",
    ),
    (
        14.1,
        22.0,
        "SPEAKER_00",
        "Айбек, подготовь обновлённую смету по складу до пятницы. Керек болса, Данамен бірге отырыңдар.",
        "mixed",
    ),
    (
        22.3,
        27.5,
        "SPEAKER_02",
        "Жақсы, пятницаға дейін жасаймын. Данамен бүгін кездесемін.",
        "mixed",
    ),
    (
        27.8,
        36.0,
        "SPEAKER_00",
        "Дана, ты согласуй с юристами договор аренды до конца следующей недели. Это срочно, без него не стартуем.",
        "ru",
    ),
    (
        36.2,
        44.5,
        "SPEAKER_01",
        "Түсінікті. Тағы бір мәселе: IT-бөлім жаңа қоймаға интернет тартуы керек, бұл айдың соңына дейін.",
        "kk",
    ),
    (
        44.8,
        50.1,
        "SPEAKER_00",
        "Тогда Айбек ещё передай айтишникам заявку на подключение склада, срок конец месяца. Все свободны.",
        "ru",
    ),
]


def _find(participants: list[Participant], name: str) -> int | None:
    for p in participants:
        if p.name.lower().startswith(name.lower()):
            return p.id
    return None


def _end_of_month(d: date) -> date:
    nxt = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return nxt - timedelta(days=1)


def _next_weekday(d: date, weekday: int) -> date:
    days = (weekday - d.weekday()) % 7 or 7
    return d + timedelta(days=days)


def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage = "ru",
    progress: ProgressCallback | None = None,
) -> MeetingResult:
    for i, stage in enumerate(_STAGES):
        if progress:
            progress(stage, (i + 1) / len(_STAGES))

    segments = [
        Segment(start=s, end=e, speaker=sp, text=t, lang=lang) for s, e, sp, t, lang in _SEGMENTS
    ]

    aibek = _find(participants, "Айбек")
    dana = _find(participants, "Дана")
    chair = participants[0].id if participants else None

    speaker_map = [
        SpeakerMapping(speaker="SPEAKER_00", participant_id=chair, source="llm", confidence=0.71),
        SpeakerMapping(
            speaker="SPEAKER_01", participant_id=dana, source="voiceprint", confidence=0.88
        ),
        SpeakerMapping(
            speaker="SPEAKER_02", participant_id=aibek, source="voiceprint", confidence=0.92
        ),
    ]

    def pick(direction: str) -> str:
        return (
            direction if direction in directions else (directions[-1] if directions else "Другое")
        )

    friday = _next_weekday(meeting_date, 4)
    eom = _end_of_month(meeting_date)
    next_week_end = _next_weekday(meeting_date, 6) + timedelta(days=7)

    tasks = [
        Task(
            text="Подготовить обновлённую смету по новому складу",
            assignee_participant_id=aibek,
            assignee_name="Айбек",
            deadline=friday,
            deadline_raw="до пятницы",
            urgency="high",
            direction=pick("Финансы"),
            quote="Айбек, подготовь обновлённую смету по складу до пятницы.",
            segment_index=2,
            confidence=0.93,
        ),
        Task(
            text="Согласовать договор аренды склада с юристами",
            assignee_participant_id=dana,
            assignee_name="Дана",
            deadline=next_week_end,
            deadline_raw="до конца следующей недели",
            urgency="critical",
            direction=pick("Юридическое"),
            quote="Дана, ты согласуй с юристами договор аренды до конца следующей недели.",
            segment_index=4,
            confidence=0.9,
        ),
        Task(
            text="Встретиться с Даной по смете склада",
            assignee_participant_id=aibek,
            assignee_name="Айбек",
            deadline=meeting_date,
            deadline_raw="бүгін",
            urgency="normal",
            direction=pick("Финансы"),
            quote="Данамен бүгін кездесемін.",
            segment_index=3,
            confidence=0.78,
        ),
        Task(
            text="Передать в ИТ заявку на подключение интернета на новом складе",
            assignee_participant_id=aibek,
            assignee_name="Айбек",
            deadline=eom,
            deadline_raw="конец месяца",
            urgency="normal",
            direction=pick("ИТ"),
            quote="Айбек ещё передай айтишникам заявку на подключение склада, срок конец месяца.",
            segment_index=6,
            confidence=0.85,
        ),
    ]

    if output_language == "kk":
        summary = (
            "## Тақырып\nIV тоқсан бюджеті және жаңа қойманы іске қосу.\n\n"
            "## Шешімдер\n- Қойма сметасы жаңартылады.\n- Жалдау шарты заңгерлермен келісіледі.\n\n"
            "## Тапсырмалар\n- Айбек: смета (жұма), ИТ-ге өтінім (ай соңы).\n- Дана: жалдау шарты (келесі апта соңы).\n\n"
            "## Ашық сұрақтар\n- Смета әлі бекітілмеген."
        )
    else:
        summary = (
            "## Тема\nБюджет на IV квартал и запуск нового склада.\n\n"
            "## Решения\n- Смета по складу будет обновлена.\n- Договор аренды согласуется с юристами до старта.\n\n"
            "## Поручения\n- Айбек: обновлённая смета (пятница), заявка в ИТ (конец месяца).\n- Дана: договор аренды (конец следующей недели).\n\n"
            "## Открытые вопросы\n- Смета ещё не утверждена."
        )

    total = segments[-1].end
    by_lang: dict[str, float] = {}
    for s in segments:
        by_lang[s.lang] = by_lang.get(s.lang, 0.0) + (s.end - s.start)
    language_stats = {k: round(v / total, 2) for k, v in by_lang.items()}

    return MeetingResult(
        segments=segments,
        speaker_map=speaker_map,
        tasks=tasks,
        summary=summary,
        language_stats=language_stats,
        duration_sec=total,
        model_info={"stt": "fake", "diarize": "fake", "llm": "fake"},
    )


def enroll_voice(audio_path: str) -> list[float]:
    seed = sum(ord(c) for c in audio_path) % 97
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(192)]

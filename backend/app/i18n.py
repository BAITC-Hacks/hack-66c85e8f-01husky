"""Labels used in generated meeting protocols."""

LABELS = {
    "ru": {
        "organization": "Протокол совещания",
        "date": "Дата",
        "participants": "Участники",
        "summary": "Краткое содержание",
        "tasks": "Поручения",
        "number": "№",
        "assignee": "Ответственный",
        "task": "Поручение",
        "deadline": "Срок",
        "urgency": "Срочность",
        "direction": "Направление",
        "transcript": "Транскрипт",
        "low": "Низкая",
        "normal": "Обычная",
        "high": "Высокая",
        "critical": "Критическая",
    },
    "kk": {
        "organization": "Жиналыс хаттамасы",
        "date": "Күні",
        "participants": "Қатысушылар",
        "summary": "Қысқаша мазмұны",
        "tasks": "Тапсырмалар",
        "number": "№",
        "assignee": "Жауапты",
        "task": "Тапсырма",
        "deadline": "Мерзімі",
        "urgency": "Шұғылдығы",
        "direction": "Бағыты",
        "transcript": "Транскрипт",
        "low": "Төмен",
        "normal": "Қалыпты",
        "high": "Жоғары",
        "critical": "Өте шұғыл",
    },
}


def labels(lang: str) -> dict[str, str]:
    """Return protocol labels for a supported language."""
    try:
        return LABELS[lang]
    except KeyError as exc:
        raise ValueError("lang must be 'ru' or 'kk'") from exc

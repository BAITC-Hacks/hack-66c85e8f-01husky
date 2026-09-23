"""Relative dates use the meeting date, never wall-clock time. Week end = Friday."""

import calendar
import re
from datetime import date, timedelta

TEMPORAL = re.compile(
    r"\d|сегодня|завтра|недел|месяц|пятниц|понедельник|вторник|сред[уыа]|четверг|"
    r"суббот|воскресень|день|дня|дней|январ|феврал|март|апрел|ма[яй]|июн|июл|август|"
    r"сентябр|октябр|ноябр|декабр|бүгін|ертең|бүрсігүні|апта|айдың|күн|жұма|сенбі",
    re.IGNORECASE,
)
COMMON_DEADLINE = re.compile(
    r"(?:до\s+)?конца\s+(?:(?:этой|следующей)\s+)?(?:недели|месяца)|на этой неделе|"
    r"(?:через|за|в течение|не (?:более|больше))\s+"
    r"(?:(?:\d+|один|одну|два|две|три|четыре|пять|одного|одной|двух|трех)\s+)?"
    r"(?:недел\w*|месяц\w*|дня|дней|день)|послезавтра|завтра|сегодня|ертең|бүгін|бүрсігүні",
    re.IGNORECASE,
)


def grounded_deadline(raw: str | None, quote: str) -> str | None:
    """Only an actual temporal phrase in the quote; repair omitted common expressions."""
    limit = re.search(
        r"(?:максимум|не больше|не более)\s+\d+\s+(?:день|дня|дней|күн)", quote, re.IGNORECASE
    )
    if limit:
        return limit[0]
    if raw and raw in quote and TEMPORAL.search(raw):
        return raw
    match = COMMON_DEADLINE.search(quote)
    return match[0] if match else None


def normalize_deadline(raw: str | None, meeting_date: date) -> date | None:
    if not raw:
        return None
    value = raw.lower().strip().replace("ё", "е")
    limit = re.search(r"(?:максимум|не больше|не более)\s+(\d+)\s+(?:день|дня|дней|күн)", value)
    if limit:
        return meeting_date + timedelta(days=int(limit[1]))
    if value in ("неделя", "неделю"):
        return meeting_date + timedelta(days=7)
    if re.search(r"следующ\w* недели|келесі апта", value) and re.search(r"конц|соң", value):
        return meeting_date + timedelta(days=11 - meeting_date.weekday())
    if re.search(r"на этой неделе|в течение этой недели|осы апта", value):
        return meeting_date + timedelta(days=(4 - meeting_date.weekday()) % 7)
    if re.search(r"послезавтра|бүрсігүні", value):
        return meeting_date + timedelta(days=2)
    if re.search(r"завтра|ертең", value):
        return meeting_date + timedelta(days=1)
    if re.search(r"сегодня|бүгін", value):
        return meeting_date
    if re.search(r"конца (?:этой )?недели|апта(?:ның)? соңына", value):
        return meeting_date + timedelta(days=(4 - meeting_date.weekday()) % 7)
    if re.search(r"конца (?:этого )?месяца|айдың соңына", value):
        return meeting_date.replace(
            day=calendar.monthrange(meeting_date.year, meeting_date.month)[1]
        )
    if re.search(r"через неделю", value):
        return meeting_date + timedelta(days=7)
    # Fixed durations: 'за две недели', 'в течение недели', 'за месяц', 'через 3 дня'.
    duration = re.search(
        r"(?:через|за|в течение|не (?:более|больше))\s+"
        r"(?:(\d+|один|одну|два|две|три|четыре|пять|одного|одной|двух|трех)\s+)?"
        r"(недел\w*|месяц\w*|дня|дней|день)",
        value,
    )
    if duration:
        amount, unit = duration.groups()
        numbers = {
            "один": 1,
            "одну": 1,
            "одного": 1,
            "одной": 1,
            "два": 2,
            "две": 2,
            "двух": 2,
            "три": 3,
            "трех": 3,
            "четыре": 4,
            "пять": 5,
        }
        n = int(amount) if amount and amount.isdigit() else numbers.get(amount, 1)
        if unit.startswith("месяц"):
            year, month = divmod(meeting_date.year * 12 + meeting_date.month - 1 + n, 12)
            return date(
                year, month + 1, min(meeting_date.day, calendar.monthrange(year, month + 1)[1])
            )
        return meeting_date + timedelta(days=n * (7 if unit.startswith("недел") else 1))
    duration = re.fullmatch(r"(?:максимум\s+)?(\d+)\s+(день|дня|дней|күн)", value)
    if duration:
        return meeting_date + timedelta(days=int(duration[1]))
    if re.search(r"келесі аптаға дейін|до (?:начала )?следующей недели", value):
        return meeting_date + timedelta(days=7 - meeting_date.weekday())
    match = re.search(r"через (\d+) (?:дн|день)|(?:\b)(\d+) күннен кейін", value)
    if match:
        return meeting_date + timedelta(days=int(match[1] or match[2]))
    weekdays = [
        "понедельник|дүйсенбі",
        "вторник|сейсенбі",
        "сред|сәрсенбі",
        "четверг|бейсенбі",
        "пятниц|жұма",
        "суббот|сенбі",
        "воскресень|жексенбі",
    ]
    for index, pattern in enumerate(weekdays):
        if re.search(r"\b(?:" + pattern + r")", value):
            delta = (index - meeting_date.weekday()) % 7
            if re.search(r"следующ|келесі", value):
                delta = 7 - meeting_date.weekday() + index
            return meeting_date + timedelta(days=delta)
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", value)
    if match:
        try:
            return date(*map(int, match.groups()))
        except ValueError:
            return None
    match = re.search(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?\b", value)
    if match:
        try:
            return date(int(match[3] or meeting_date.year), int(match[2]), int(match[1]))
        except ValueError:
            return None
    return None

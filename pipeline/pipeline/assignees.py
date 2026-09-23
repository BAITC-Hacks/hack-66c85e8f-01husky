"""Conservative matching: first names, case endings and transliteration; no patronymic guess."""

import re
from difflib import SequenceMatcher

from pipeline.models import Participant

_CYR = dict(
    zip(
        "абвгдеёзийклмнопрстуфхцэыьъ",
        [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "e",
            "z",
            "i",
            "i",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "h",
            "ts",
            "e",
            "y",
            "",
            "",
        ],
        strict=True,
    )
)
_CYR.update(
    {
        "ж": "zh",
        "ч": "ch",
        "ш": "sh",
        "щ": "sh",
        "ю": "yu",
        "я": "ya",
        "ә": "a",
        "ғ": "g",
        "қ": "k",
        "ң": "n",
        "ө": "o",
        "ұ": "u",
        "ү": "u",
        "і": "i",
    }
)


def tokens(name: str) -> list[str]:
    return [
        "".join(_CYR.get(c, c) for c in word) for word in re.findall(r"[^\W\d_]+", name.lower())
    ]


def _same_name(word: str, name: str) -> bool:
    if word == name:
        return True
    # Inflect the known name, never trim patronymics to a different person's first name.
    forms = {
        name + ending for ending in ("a", "u", "om", "e", "ga", "ge", "ka", "ke", "nyn", "nin")
    }
    if name.endswith("a"):
        forms |= {name[:-1] + ending for ending in ("y", "e", "u", "oi")}
    return word in forms


def resolve_assignee(name: str, participants: list[Participant]) -> int | None:
    query = tokens(name)
    if not query:
        return None
    exact = [p.id for p in participants if tokens(p.name) == query]
    if len(exact) == 1:
        return exact[0]
    matches = []
    for participant in participants:
        known = tokens(participant.name)
        if not known or not _same_name(query[0], known[0]):
            continue
        # Additional words must also agree (don't match two different Ерланы by first name).
        if len(query) > len(known) or any(
            not _same_name(q, k) for q, k in zip(query[1:], known[1:])
        ):
            continue
        matches.append(participant.id)
    if matches:
        return matches[0] if len(matches) == 1 else None
    # A small ASR spelling error in a long first name, backed by the SAME full patronymic.
    # Never fuzzy-match a bare first name or choose among multiple similar people.
    if len(query) >= 2 and len(query[0]) >= 6:
        close = []
        for p in participants:
            known = tokens(p.name)
            if (
                len(known) == len(query)
                and len(known[0]) == len(query[0])
                and sum(a != b for a, b in zip(query[0], known[0], strict=True)) == 1
                and SequenceMatcher(None, query[0], known[0]).ratio() >= 0.84
                and all(_same_name(q, k) for q, k in zip(query[1:], known[1:], strict=True))
            ):
                close.append(p.id)
        if len(close) == 1:
            return close[0]
    return None


def name_in_evidence(name: str, evidence: str) -> bool:
    query, words = tokens(name), tokens(evidence)
    return bool(query) and any(
        _same_name(word, query[0]) or _same_name(query[0], word) for word in words
    )


def grounded_name(name: str, evidence: str) -> str:
    """Drop surname/patronymic completions invented from the participant list.

    'Ерлан' in evidence cannot distinguish two Ерланы, even if the model returns a full name.
    """
    parts = re.findall(r"[^\W\d_]+", name)
    words = tokens(evidence)
    kept = []
    for part in parts:
        token = tokens(part)[0]
        if not any(_same_name(w, token) or _same_name(token, w) for w in words):
            break
        kept.append(part)
    return " ".join(kept)


def is_person_name(name: str) -> bool:
    """Do not turn role labels, pronouns or anonymous speaker IDs into guest records."""
    words = re.findall(r"[^\W\d_]+", name)
    excluded = {
        "я",
        "мы",
        "вы",
        "ты",
        "он",
        "она",
        "они",
        "все",
        "участник",
        "неизвестно",
        "неизвестный",
        "ответственный",
        "секретарь",
        "юрист",
        "директор",
        "руководитель",
        "подрядчик",
        "поставщик",
        "команда",
        "отдел",
        "мен",
        "біз",
        "сіз",
        "ол",
        "unknown",
    }
    return bool(
        2 <= len(name) <= 255
        and 1 <= len(words) <= 4
        and not re.search(r"\d|speaker", name, re.IGNORECASE)
        and all(w[0].isupper() and w.casefold() not in excluded for w in words)
        and re.fullmatch(r"[^\W\d_]+(?:[ -][^\W\d_]+){0,3}", name)
    )


def normalize_guest_name(name: str) -> str:
    """Only unambiguous patronymic endings; do not guess gender/case of a surname."""
    parts = name.strip().split()
    for i in range(1, len(parts)):
        parts[i] = re.sub(r"((?:ов|ев)н)[ыеу]$", r"\1а", parts[i])
        parts[i] = re.sub(r"((?:ов|ев)ич)[ау]$", r"\1", parts[i])
    return " ".join(parts)

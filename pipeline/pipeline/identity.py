"""Conservative speaker identities from explicit self-introduction or handing over the floor.

Not voice biometrics. Names of task recipients alone never identify the following voice.
"""

import re

from pydantic import BaseModel, Field

from pipeline.assignees import grounded_name, is_person_name, name_in_evidence, resolve_assignee
from pipeline.extract import _chunks
from pipeline.models import Participant, Segment, SpeakerMapping


class IdentityHint(BaseModel):
    name: str
    evidence_index: int = Field(ge=0)
    quote: str
    response_index: int = Field(ge=0)


class Identities(BaseModel):
    hints: list[IdentityHint]


HANDOFF = re.compile(
    r"начн[её]м\s+с|(?:передаю|предоставляю)\s+слово|вам\s+слово|"
    r"(?:давайте\s+)?послушаем|доложите|расскажите|сөз\s+бер|бастайық|бастасақ",
    re.IGNORECASE,
)
SELF = re.compile(r"меня\s+зовут|менің\s+атым|это\s+я\b", re.IGNORECASE)


def identify_speakers(
    segments: list[Segment],
    mappings: list[SpeakerMapping],
    participants: list[Participant],
    llm,
) -> tuple[list[SpeakerMapping], int]:
    if not segments:
        return mappings, 0
    evidence: dict[str, dict[str, tuple[int | None, str]]] = {}
    accepted = 0
    for chunk in _chunks(segments):
        # No suggestive phrases, no model call and no identity guesses.
        if not any(HANDOFF.search(s["text"]) or SELF.search(s["text"]) for s in chunk):
            continue
        hints = llm.complete(
            "Определи личность голоса ТОЛЬКО по явному представлению ('меня зовут…') или "
            "передаче слова ('Начнём с Ботагоз Нурлановны', 'Тимур, вам слово', 'доложите'). "
            "После передачи слова response_index — ближайшая СОДЕРЖАТЕЛЬНАЯ ответная реплика "
            "другого speaker, не краткое 'да/хорошо' третьего человека. evidence_index и quote — "
            "дословная цитата передачи слова/представления, name — имя именно из этой цитаты "
            "в именительном падеже, в том числе если его нет в participants. "
            "При самопредставлении response_index=evidence_index. Обычное поручение другому "
            "человеку НЕ является передачей слова. Не угадывай имя по теме доклада, полу или "
            "порядку participants. Если не уверен — не добавляй hint. Индексы бери из segments.",
            {"segments": chunk, "participants": [p.name for p in participants]},
            Identities,
        )
        allowed = {s["segment_index"] for s in chunk}
        for hint in hints.hints:
            i, j = hint.evidence_index, hint.response_index
            if i not in allowed or j not in allowed or not hint.quote.strip():
                continue
            source, response = segments[i], segments[j]
            if hint.quote not in source.text or not name_in_evidence(hint.name, hint.quote):
                continue
            name = grounded_name(hint.name, hint.quote)
            pid = resolve_assignee(name, participants)
            if not is_person_name(name):
                continue
            if pid is None and any(resolve_assignee(name, [p]) for p in participants):
                continue  # ambiguous existing people, not a new guest
            if i == j:
                if not SELF.search(hint.quote):
                    continue
            else:
                if not HANDOFF.search(hint.quote) or not i < j <= i + 4:
                    continue
                if source.speaker == response.speaker or response.start - source.end > 15:
                    continue
                if len(response.text.split()) < 4:
                    continue
                # No skipping an intervening substantive response from another voice.
                if any(
                    s.speaker != source.speaker and len(s.text.split()) >= 4
                    for s in segments[i + 1 : j]
                ):
                    continue
            key = f"id:{pid}" if pid is not None else f"name:{name.casefold()}"
            evidence.setdefault(response.speaker, {})[key] = (pid, name)
            accepted += 1
    out = []
    for mapping in mappings:
        ids = evidence.get(mapping.speaker, {})
        if mapping.source in ("manual", "voiceprint") or len(ids) != 1:
            out.append(mapping)
        else:
            pid, name = next(iter(ids.values()))
            out.append(
                SpeakerMapping(
                    speaker=mapping.speaker,
                    participant_id=pid,
                    participant_name=name,
                    source="llm",
                    confidence=0.75,
                )
            )
    return out, accepted

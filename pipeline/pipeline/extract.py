"""Candidates → literal evidence check → independent verification/classification → local summary."""

import re
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field

from pipeline.assignees import grounded_name, name_in_evidence, resolve_assignee
from pipeline.deadlines import grounded_deadline, normalize_deadline
from pipeline.llm import LocalLLMError, OllamaLLM
from pipeline.models import OutputLanguage, Participant, ProgressCallback, Segment, Task, Urgency
from pipeline.privacy import mask_sensitive
from pipeline.settings import PipelineSettings


class Candidate(BaseModel):
    segment_index: int = Field(ge=0)
    quote: str = Field(min_length=8)
    text: str = Field(min_length=3)
    assignee_name: str
    assignee_quote: str | None = None
    assignee_segment_index: int | None = None
    deadline_raw: str | None = None


class Candidates(BaseModel):
    tasks: list[Candidate] = Field(max_length=40)


class Review(BaseModel):
    candidate_index: int = Field(ge=0)
    is_task: bool
    deadline: date | None
    urgency: Urgency
    direction: str
    confidence: float = Field(ge=0, le=1)
    text: str | None = None


class Reviews(BaseModel):
    reviews: list[Review]


class Summary(BaseModel):
    summary: str


@dataclass
class Extraction:
    tasks: list[Task]
    summary: str
    rejected: int = 0


def _chunks(segments: list[Segment], budget: int = 6500) -> list[list[dict]]:
    """Bound the prompt, preserve global indices, overlap context for adjacent replies."""
    chunks, current, size = [], [], 0
    for idx, segment in enumerate(segments):
        # Extremely long provider segments are split for prompts only (quote still refers to idx).
        for offset in range(0, len(segment.text), 2500):
            item = {
                "segment_index": idx,
                "speaker": segment.speaker,
                "text": segment.text[offset : offset + 2500],
            }
            cost = len(item["text"]) + 80
            if current and size + cost > budget:
                chunks.append(current)
                current = current[-2:]
                size = sum(len(i["text"]) + 80 for i in current)
            current.append(item)
            size += cost
    if current:
        chunks.append(current)
    return chunks


def extract(
    segments: list[Segment],
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage,
    settings: PipelineSettings,
    progress: ProgressCallback | None = None,
    *,
    llm=None,
) -> Extraction:
    if not segments:
        return Extraction([], "")
    llm = llm or OllamaLLM(settings)
    tasks, rejected, seen, summaries = [], 0, set(), []
    chunks = _chunks(segments)
    for chunk_idx, chunk in enumerate(chunks):
        if progress:
            progress("extract", 0.76 + 0.22 * chunk_idx / len(chunks))
        base = {
            "meeting_date": meeting_date.isoformat(),
            "output_language": output_language,
            "participants": [{"id": p.id, "name": p.name} for p in participants],
            "directions": directions,
            "segments": chunk,
        }
        candidates = llm.complete(
            "Ты секретарь совещания. Извлеки ВСЕ конкретные поручения и обещания будущей работы "
            "на русском, казахском и смешанной речи. Не включай отчеты о сделанном, пожелания, "
            "вопросы и отмененные/условные предложения. Фраза 'пусть Ерлан до конца недели "
            "подготовит претензию' — поручение Ерлану, даже если его нет в participants. "
            "text — краткое действие на языке output_language, без имени и срока (для них есть "
            "отдельные поля). quote — точная цитата из ОДНОГО "
            "segments[segment_index], без перефразирования. segment_index бери из данных. "
            "assignee_name — явно названный исполнитель, НЕ тот, кто раздает поручение. "
            "Не дополняй имя по списку участников. assignee_quote — дословная цитата, содержащая "
            "имя исполнителя; assignee_segment_index — её индекс. Для 'я подготовлю' без имени "
            "используй метку speakerN текущей реплики. Если ответственный неизвестен — пустая "
            "строка и null для assignee_quote/assignee_segment_index. deadline_raw — дословные "
            "слова срока из quote или null. Не выдумывай срок. Если задач нет — tasks=[].",
            base,
            Candidates,
        )
        valid = []
        allowed_indices = {s["segment_index"] for s in chunk}
        for candidate in candidates.tasks:
            i = candidate.segment_index
            if i not in allowed_indices or candidate.quote not in segments[i].text:
                rejected += 1
                continue
            key = (i, candidate.quote.casefold().strip(), candidate.text.casefold().strip())
            if key in seen:
                continue
            seen.add(key)
            candidate.deadline_raw = grounded_deadline(candidate.deadline_raw, candidate.quote)
            name = candidate.assignee_name.strip()
            if not name:
                # A literal explicit appointment survives even if the model omits the name field.
                appointed = re.search(
                    r"\bпусть\s+([А-ЯӘҒҚҢӨҰҮҺІA-Z][а-яәғқңөұүһіa-z]+)", candidate.quote
                )
                if appointed:
                    name = appointed[1]
            if not name and re.search(
                r"\b(я|мен|өзім|подготовлю|дам|составлю|отправлю|обновлю|дайындаймын|жіберемін)\b",
                candidate.quote,
                re.IGNORECASE,
            ):
                name = segments[i].speaker
            if name == segments[i].speaker:
                # Accept a speaker label only when the quote actually expresses self-assignment.
                if not re.search(
                    r"\b(я|мен|өзім|подготовлю|дам|составлю|отправлю|обновлю|дайындаймын|жіберемін)\b",
                    candidate.quote,
                    re.IGNORECASE,
                ):
                    name = ""
            elif name:
                ai, aq = candidate.assignee_segment_index, candidate.assignee_quote
                if name_in_evidence(name, candidate.quote):
                    ai, aq = i, candidate.quote
                if (
                    ai is None
                    or ai not in allowed_indices
                    or abs(ai - i) > 3
                    or not aq
                    or aq not in segments[ai].text
                    or not name_in_evidence(name, aq)
                ):
                    name = ""
                else:
                    name = grounded_name(name, aq)
            if not name:
                appointed = re.search(
                    r"\bпусть\s+([А-ЯӘҒҚҢӨҰҮҺІA-Z][а-яәғқңөұүһіa-z]+)",
                    candidate.quote,
                )
                if appointed:
                    name = appointed[1]
            candidate.assignee_name = name
            valid.append(candidate)
        if valid:
            if progress:
                progress("extract", 0.76 + 0.22 * (chunk_idx + 0.4) / len(chunks))
            reviews = llm.complete(
                "Независимо проверь кандидатов поручений по ИХ ЦИТАТАМ. is_task=true только "
                "для конкретного согласованного будущего действия; false для отчета о прошлом, "
                "отмены, гипотезы, вопроса, простого описания проблемы. Само действие text ДОЛЖНО "
                "быть прямо выражено в quote. Даже если оно обсуждалось рядом, цитата '3-4 компании "
                "постоянно так делают' НЕ доказывает 'подготовить уведомление': is_task=false. "
                "text в ответе — только краткое действие в инфинитиве, без имени/срока, ничего "
                "не добавляй к цитате. Для каждого candidate_index "
                "верни одну запись. deadline — ISO дата относительно meeting_date и deadline_raw, "
                "не текущей даты. Нет срока или он неоднозначен — null. Конец недели = ближайшая "
                "пятница. urgency: normal по умолчанию, high если явно срочно, critical только "
                "авария/критическая ситуация. direction только из directions, иначе Другое. "
                "confidence отражает уверенность в поручении, а не голосе.",
                {
                    "meeting_date": meeting_date.isoformat(),
                    "output_language": output_language,
                    "directions": directions,
                    "candidates": [
                        {"candidate_index": i, **c.model_dump()} for i, c in enumerate(valid)
                    ],
                },
                Reviews,
            )
            reviewed = set()
            for review in reviews.reviews:
                if review.candidate_index >= len(valid) or review.candidate_index in reviewed:
                    continue
                reviewed.add(review.candidate_index)
                if not review.is_task:
                    rejected += 1
                    continue
                c = valid[review.candidate_index]
                if re.fullmatch(
                    r"(?:вы\s+)?(?:главн\w*\s+)?сроки не затяните[.!]?",
                    c.quote.strip(),
                    re.IGNORECASE,
                ):
                    rejected += 1
                    continue
                deadline = normalize_deadline(c.deadline_raw, meeting_date)
                if deadline is None and c.deadline_raw:
                    deadline = review.deadline
                tasks.append(
                    Task(
                        text=mask_sensitive(review.text or c.text),
                        assignee_name=mask_sensitive(c.assignee_name),
                        assignee_participant_id=resolve_assignee(c.assignee_name, participants),
                        deadline=deadline,
                        deadline_raw=c.deadline_raw,
                        urgency=review.urgency,
                        direction=review.direction if review.direction in directions else "Другое",
                        quote=c.quote,
                        segment_index=c.segment_index,
                        confidence=min(review.confidence, 0.95),
                    )
                )
            if reviewed != set(range(len(valid))):
                raise LocalLLMError("Local LLM omitted task verification results; retry processing")
        if progress:
            progress(
                "summary" if chunk_idx == len(chunks) - 1 else "extract",
                0.76 + 0.22 * (chunk_idx + 0.75) / len(chunks),
            )
        summary = llm.complete(
            "Составь краткое саммари фрагмента совещания (3–6 предложений) на output_language: "
            "основные обсужденные проблемы и принятые решения. Не добавляй новых фактов, имён "
            "или поручений. Различай запланированное и уже выполненное.",
            base,
            Summary,
        )
        summaries.append(mask_sensitive(summary.summary))
        if progress:
            progress(
                "summary" if chunk_idx == len(chunks) - 1 else "extract",
                0.76 + 0.22 * (chunk_idx + 1) / len(chunks),
            )
    # Adjacent chunks share context; remove repeated actions with identical evidence.
    unique = {}
    for task in tasks:
        key = (task.text.casefold().strip(), task.assignee_name.casefold())
        unique[key] = task  # later repetition carries the latest stated deadline
    return Extraction(list(unique.values()), "\n\n".join(summaries), rejected)

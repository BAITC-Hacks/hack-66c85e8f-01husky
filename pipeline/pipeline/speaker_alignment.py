"""Assign ASR words to acoustic turns; never infer a name from words or participant order."""

import re
from dataclasses import dataclass

from pipeline.diarization import SpeakerTurn
from pipeline.models import Segment, SpeakerMapping
from pipeline.privacy import mask_sensitive, mask_sensitive_parts
from pipeline.stt.local_whisper import TranscriptSegment, TranscriptWord


@dataclass
class Alignment:
    segments: list[Segment]
    speaker_map: list[SpeakerMapping]
    nearest_words: int = 0
    distant_words: int = 0
    overlapping_words: int = 0
    coarse_segments: int = 0
    adjusted_boundary_words: int = 0


def join_continuations(segments: list[Segment]) -> list[Segment]:
    """Join ASR line wraps within a single speaker's sentence, never across a speaker change."""
    out: list[Segment] = []
    for segment in segments:
        if (
            out
            and out[-1].speaker == segment.speaker
            and segment.start - out[-1].end <= 0.7
            and segment.end - out[-1].start <= 20
            and len(out[-1].text) + len(segment.text) < 700
            and not re.search(r'[.!?…][»”"\']?$', out[-1].text.strip())
        ):
            out[-1].text += " " + segment.text
            out[-1].end = segment.end
        else:
            out.append(segment.model_copy())
    return out


def _stabilize_sentence_tail(words, assignments, turns, grace: float) -> int:
    """Delay a small mid-sentence jitter to the sentence end, not across a clear turn.

    Only a short tail of a single ASR segment, no pause/overlap, terminal punctuation,
    and a continuing next acoustic turn. A real interruption can still fool this heuristic;
    keep diagnostics and allow disabling it. Never merge clusters or infer identities.
    """
    if not grace or len(words) < 3:
        return 0
    changes = [i for i in range(1, len(words)) if assignments[i][0] != assignments[i - 1][0]]
    if len(changes) != 1:
        return 0
    i = changes[0]
    if i < 2 or words[-1].end - words[i].start > grace:
        return 0
    if not re.search(r'[.!?…][»”"\']?$', words[-1].text.strip()):
        return 0
    if re.search(r'[.!?…:][»”"\']?$', words[i - 1].text.strip()):
        return 0
    if any(words[j].start - words[j - 1].end >= 0.20 for j in range(i, len(words))):
        return 0
    if any(a[1] or a[2] for a in assignments):
        return 0
    # Earlier cross-talk must not disable correction of a later, clean boundary.
    if any(a[3] for a in assignments[i - 1 :]):
        return 0
    old, new = assignments[0][0], assignments[-1][0]
    if not any(t.speaker == new and t.end >= words[-1].end + 1.5 for t in turns):
        return 0
    for j in range(i, len(words)):
        assignments[j] = (old, *assignments[j][1:])
    return len(words) - i


def _speaker_for(
    start: float,
    end: float,
    turns: list[SpeakerTurn],
    previous: int | None,
) -> tuple[int, bool, bool, bool]:
    scores: dict[int, float] = {}
    for turn in turns:
        overlap = max(0.0, min(end, turn.end) - max(start, turn.start))
        if end <= start and turn.start <= start < turn.end:
            overlap = 0.001
        if overlap > 0:
            scores[turn.speaker] = scores.get(turn.speaker, 0.0) + overlap
    if scores:
        best = max(scores.values())
        tied = [speaker for speaker, score in scores.items() if abs(score - best) < 1e-6]
        speaker = previous if previous in tied else tied[0]
        simultaneous = any(
            a.speaker != b.speaker and min(end, a.end, b.end) > max(start, a.start, b.start)
            for i, a in enumerate(turns)
            if a.start < end and a.end > start
            for b in turns[i + 1 :]
            if b.start < end and b.end > start
        )
        return speaker, False, False, simultaneous

    # VAD/ASR boundaries do not match exactly. Keep diagnostics for manual review.
    def distance(turn: SpeakerTurn) -> float:
        return max(turn.start - end, start - turn.end, 0.0)

    closest = min(turns, key=distance)
    return closest.speaker, True, distance(closest) > 0.75, False


def align_speakers(
    transcript: list[TranscriptSegment],
    turns: list[SpeakerTurn],
    *,
    boundary_grace: float = 0,
) -> Alignment:
    result = Alignment([], [])
    if not transcript:
        return result
    if not turns:
        raise RuntimeError("Speech was transcribed but no speakers were detected; review the audio")
    turns = sorted(turns, key=lambda turn: (turn.start, turn.end, turn.speaker))
    labels: dict[int, str] = {}
    previous = None
    for segment in transcript:
        words = segment.words
        if not words or mask_sensitive("".join(w.text for w in words).strip()) != segment.text:
            # Keep all text if a provider lacks word timestamps or returns inconsistent words.
            words = [TranscriptWord(segment.start, segment.end, segment.text)]
            result.coarse_segments += 1
        current: Segment | None = None
        assignments = []
        for word in words:
            assigned = _speaker_for(word.start, word.end, turns, previous)
            assignments.append(assigned)
            previous = assigned[0]
        result.adjusted_boundary_words += _stabilize_sentence_tail(
            words,
            assignments,
            turns,
            boundary_grace,
        )
        for word, assigned in zip(words, assignments, strict=True):
            if not word.text.strip():
                if current:
                    current.text += word.text
                continue
            speaker, nearest, distant, overlap = assigned
            result.nearest_words += nearest
            result.distant_words += distant
            result.overlapping_words += overlap
            previous = speaker
            label = labels.setdefault(speaker, f"speaker{len(labels) + 1}")
            if current is None or current.speaker != label:
                current = Segment(
                    start=word.start,
                    end=max(word.end, word.start),
                    speaker=label,
                    text=word.text,
                    lang="other",
                )
                result.segments.append(current)
            else:
                current.text += word.text
                current.end = max(current.end, word.end)
    masked = mask_sensitive_parts([segment.text.strip() for segment in result.segments])
    for segment, text in zip(result.segments, masked, strict=True):
        segment.text = text
    result.speaker_map = [
        SpeakerMapping(speaker=label, participant_id=None, source="none", confidence=0.0)
        for label in labels.values()
    ]
    return result

"""Assign ASR words to acoustic turns; never infer a name from words or participant order."""

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


def align_speakers(transcript: list[TranscriptSegment], turns: list[SpeakerTurn]) -> Alignment:
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
        for word in words:
            if not word.text.strip():
                if current:
                    current.text += word.text
                continue
            speaker, nearest, distant, overlap = _speaker_for(word.start, word.end, turns, previous)
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

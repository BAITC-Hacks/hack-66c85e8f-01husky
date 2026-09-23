"""Conservative pattern-based masking, not full anonymization of personal data."""

import re

IIN = re.compile(r"(?<!\w)\d{12}(?!\w)")
PHONE = re.compile(r"(?<!\w)(?:\+7|8)[ ()\t.-]*(?:\d[ ()\t.-]*){9}\d(?!\w)")


def mask_sensitive(text: str) -> str:
    return PHONE.sub("[PHONE]", IIN.sub("[IIN]", text))


def mask_sensitive_parts(parts: list[str]) -> list[str]:
    """Mask even when a phone spans an ASR/speaker boundary, without merging turns."""
    joined = " ".join(parts)
    spans: list[tuple[int, int, str]] = []
    for pattern, label in ((IIN, "[IIN]"), (PHONE, "[PHONE]")):
        for match in pattern.finditer(joined):
            if not any(match.start() < end and match.end() > start for start, end, _ in spans):
                spans.append((match.start(), match.end(), label))
    spans.sort()
    result, offset = [], 0
    for part in parts:
        chunks, cursor = [], 0
        for start, end, label in spans:
            left, right = max(0, start - offset), min(len(part), end - offset)
            if left < right:
                chunks.extend((part[cursor:left], label))
                cursor = right
        chunks.append(part[cursor:])
        result.append("".join(chunks))
        offset += len(part) + 1
    return result

"""Conservative pattern-based masking, not full anonymization of personal data."""

import re

IIN = re.compile(r"(?<!\w)\d{12}(?!\w)")
PHONE = re.compile(r"(?<!\w)(?:\+7|8)[ ()\t.-]*(?:\d[ ()\t.-]*){9}\d(?!\w)")


def mask_sensitive(text: str) -> str:
    return PHONE.sub("[PHONE]", IIN.sub("[IIN]", text))

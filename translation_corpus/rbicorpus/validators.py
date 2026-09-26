"""Deterministic checks that an English text and its Hindi counterpart agree.

A failed check means "flag for review", never "silently drop": official
translations sometimes spell a number out in words, which a mechanical check
cannot tell apart from a real error.
"""

import re
import unicodedata
from collections import Counter

from .normalize import to_ascii_digits

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

_EN_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_HI_MONTHS_RAW = {
    "जनवरी": 1, "फरवरी": 2, "फ़रवरी": 2, "मार्च": 3, "अप्रैल": 4, "अप्रेल": 4,
    "मई": 5, "जून": 6, "जुलाई": 7, "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9,
    "अक्टूबर": 10, "अक्तूबर": 10, "नवंबर": 11, "नवम्बर": 11,
    "दिसंबर": 12, "दिसम्बर": 12,
}
_HI_MONTHS = {unicodedata.normalize("NFC", k): v for k, v in _HI_MONTHS_RAW.items()}

_EN_MONTH_ALT = "|".join(sorted(_EN_MONTHS, key=len, reverse=True))
_HI_MONTH_ALT = "|".join(sorted(_HI_MONTHS, key=len, reverse=True))

_DATE_PATTERNS = [
    # 26 September 2026 / 26th Sept, 2026
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_EN_MONTH_ALT})\.?,?\s+(\d{{4}})\b", re.I), "dmy_en"),
    # September 26, 2026
    (re.compile(rf"\b({_EN_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I), "mdy_en"),
    # 26 सितंबर 2026 / 26 सितंबर, 2026
    (re.compile(rf"(\d{{1,2}})\s+({_HI_MONTH_ALT}),?\s+(\d{{4}})"), "dmy_hi"),
    # सितंबर 26, 2026
    (re.compile(rf"({_HI_MONTH_ALT})\s+(\d{{1,2}}),?\s+(\d{{4}})"), "mdy_hi"),
    # 26.09.2026 / 26/09/2026 / 26-09-2026
    (re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b"), "dmy_num"),
    # 2026-09-26
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd_num"),
]

# Unit words whose counts must agree between the two languages.
_UNIT_PAIRS = {
    "crore": (re.compile(r"\bcrores?\b|\bcr\b\.?", re.I), re.compile(unicodedata.normalize("NFC", "करोड़|करोड"))),
    "lakh": (re.compile(r"\blakhs?\b|\blacs?\b", re.I), re.compile("लाख")),
    "percent": (re.compile(r"%|\bper\s?cent\b|\bpercent\b", re.I), re.compile("%|प्रतिशत")),
}

# Tokens like RBI/2024-25/123 or DOR.STR.REC.12/21.04.048/2024-25. Official
# Hindi versions normally keep these in Latin script, unchanged.
_REF_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-()]*/[A-Za-z0-9.\-/()]*\d[A-Za-z0-9.\-/()]*")


def extract_numbers(text: str) -> Counter:
    text = to_ascii_digits(unicodedata.normalize("NFC", text))
    values = Counter()
    for match in _NUMBER_RE.findall(text):
        value = match.replace(",", "").rstrip(".")
        if value:
            values[value] += 1
    return values


def extract_dates(text: str) -> Counter:
    text = to_ascii_digits(unicodedata.normalize("NFC", text))
    found = Counter()
    consumed = []
    for pattern, kind in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            if any(start <= m.start() < end for start, end in consumed):
                continue
            a, b, c = m.groups()
            try:
                if kind == "dmy_en":
                    d, mo, y = int(a), _EN_MONTHS[b.lower().rstrip(".")], int(c)
                elif kind == "mdy_en":
                    mo, d, y = _EN_MONTHS[a.lower().rstrip(".")], int(b), int(c)
                elif kind == "dmy_hi":
                    d, mo, y = int(a), _HI_MONTHS[b], int(c)
                elif kind == "mdy_hi":
                    mo, d, y = _HI_MONTHS[a], int(b), int(c)
                elif kind == "dmy_num":
                    d, mo, y = int(a), int(b), int(c)
                else:
                    y, mo, d = int(a), int(b), int(c)
            except KeyError:
                continue
            if 1 <= mo <= 12 and 1 <= d <= 31:
                found[f"{y:04d}-{mo:02d}-{d:02d}"] += 1
                consumed.append((m.start(), m.end()))
    return found


def extract_references(text: str) -> set[str]:
    refs = set()
    for token in _REF_TOKEN_RE.findall(to_ascii_digits(text)):
        token = token.rstrip(".,;:)")
        if re.search(r"\d", token) and "/" in token:
            refs.add(token)
    return refs


def _counter_diff(source: Counter, target: Counter) -> dict:
    return {
        "missing_in_target": dict(source - target),
        "extra_in_target": dict(target - source),
    }


def check_pair(en_text: str, hi_text: str) -> dict:
    """Compare numbers, dates, unit words and reference identifiers.

    Returns {"status": "pass" | "flag", "flags": [...], "details": {...}}.
    """
    flags = []
    details = {}

    numbers = _counter_diff(extract_numbers(en_text), extract_numbers(hi_text))
    if numbers["missing_in_target"] or numbers["extra_in_target"]:
        flags.append("number_mismatch")
        details["numbers"] = numbers

    dates = _counter_diff(extract_dates(en_text), extract_dates(hi_text))
    if dates["missing_in_target"] or dates["extra_in_target"]:
        flags.append("date_mismatch")
        details["dates"] = dates

    hi_nfc = unicodedata.normalize("NFC", hi_text)
    for unit, (en_re, hi_re) in _UNIT_PAIRS.items():
        en_count, hi_count = len(en_re.findall(en_text)), len(hi_re.findall(hi_nfc))
        if en_count != hi_count:
            flags.append(f"{unit}_count_mismatch")
            details[unit] = {"en": en_count, "hi": hi_count}

    en_refs, hi_refs = extract_references(en_text), extract_references(hi_text)
    if en_refs != hi_refs:
        flags.append("reference_mismatch")
        details["references"] = {
            "missing_in_target": sorted(en_refs - hi_refs),
            "extra_in_target": sorted(hi_refs - en_refs),
        }

    return {"status": "flag" if flags else "pass", "flags": flags, "details": details}

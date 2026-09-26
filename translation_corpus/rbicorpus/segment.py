"""Paragraph and sentence segmentation, and conservative paragraph alignment.

Alignment only pairs paragraphs when the structure makes the pairing
unambiguous (matching paragraph numbers, or identical paragraph counts).
Anything else is returned as unaligned for review rather than guessed.
"""

import re

from .validators import check_pair

_EN_ABBREVIATIONS = {
    "rs", "no", "nos", "i.e", "e.g", "viz", "ltd", "co", "pvt", "govt", "dept",
    "mr", "mrs", "ms", "dr", "shri", "smt", "sr", "jr", "st", "vs", "etc",
    "para", "paras", "sec", "art", "cl", "ch", "vol", "fig", "approx", "inc",
    "u.s", "u.k", "a.m", "p.m", "jan", "feb", "mar", "apr", "jun", "jul",
    "aug", "sep", "sept", "oct", "nov", "dec", "ref", "ibid", "cf",
}
_HI_ABBREVIATIONS = {"सं", "रु", "डॉ", "क्र", "पृ", "ई", "प्रा", "लि", "श्री", "सुश्री", "मा", "कं"}

# "1." "2.1." "(a)" "iv." at the start of a paragraph
_PARA_LABEL_RE = re.compile(r"^\s*(\(?(?:\d+(?:\.\d+)*|[a-z]|[ivxlc]+)\)|\d+(?:\.\d+)*\.?)(?=\s)", re.I)
_BOUNDARY_RE = re.compile(r"(?<=[.?!।॥])\s+")


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _protected(prev_chunk: str, lang: str) -> bool:
    """True if the full stop ending prev_chunk is not a sentence end."""
    last = prev_chunk.rstrip()
    if last.endswith(("?", "!", "।", "॥")):
        return False
    word = re.split(r"\s", last)[-1].rstrip(".")
    bare = word.strip("()[]\"'").lower()
    if not bare:
        return True
    if re.fullmatch(r"[a-z]", bare):
        return True  # initials such as "A. K. Sharma" or list markers "a."
    if re.fullmatch(r"\d+(?:\.\d+)*|[ivxlc]+", bare):
        # A bare list marker ("1.", "iv.") on its own; a number ending a longer
        # sentence ("... by 2026.") is a real sentence end.
        return len(last.split()) == 1
    abbreviations = _HI_ABBREVIATIONS if lang == "hi" else _EN_ABBREVIATIONS
    return bare in abbreviations


def split_sentences(paragraph: str, lang: str) -> list[str]:
    parts = _BOUNDARY_RE.split(paragraph.strip())
    sentences: list[str] = []
    for part in parts:
        if sentences and _protected(sentences[-1], lang):
            sentences[-1] = f"{sentences[-1]} {part}"
        else:
            sentences.append(part)
    return [s for s in sentences if s]


def paragraph_label(paragraph: str) -> str | None:
    m = _PARA_LABEL_RE.match(paragraph)
    return m.group(1).strip("().").lower() if m else None


def align_paragraphs(en_paras: list[str], hi_paras: list[str]) -> dict:
    """Pair paragraphs only when the pairing is structurally unambiguous.

    Returns {"method", "pairs": [{"en", "hi", "check"}], "unaligned_en", "unaligned_hi"}.
    """
    en_labels = [paragraph_label(p) for p in en_paras]
    hi_labels = [paragraph_label(p) for p in hi_paras]
    labelled_en = {l: p for l, p in zip(en_labels, en_paras) if l}
    labelled_hi = {l: p for l, p in zip(hi_labels, hi_paras) if l}

    unique_en = len(labelled_en) == sum(1 for l in en_labels if l)
    unique_hi = len(labelled_hi) == sum(1 for l in hi_labels if l)
    use_labels = unique_en and unique_hi and len(labelled_en) >= 2 and set(labelled_en) == set(labelled_hi)

    if use_labels and len(en_paras) == len(hi_paras) and en_labels == hi_labels:
        method = "count_and_labels"
        raw_pairs = list(zip(en_paras, hi_paras))
    elif use_labels:
        method = "labels"
        raw_pairs = [(labelled_en[l], labelled_hi[l]) for l in en_labels if l]
    elif len(en_paras) == len(hi_paras):
        method = "count"
        raw_pairs = list(zip(en_paras, hi_paras))
    else:
        return {"method": "none", "pairs": [], "unaligned_en": en_paras, "unaligned_hi": hi_paras}

    paired_en = {id(e) for e, _ in raw_pairs}
    paired_hi = {id(h) for _, h in raw_pairs}
    return {
        "method": method,
        "pairs": [{"en": e, "hi": h, "check": check_pair(e, h)} for e, h in raw_pairs],
        "unaligned_en": [p for p in en_paras if id(p) not in paired_en],
        "unaligned_hi": [p for p in hi_paras if id(p) not in paired_hi],
    }

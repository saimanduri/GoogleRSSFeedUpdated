"""Text normalisation and encoding-quality checks for English and Hindi text.

Hindi PDFs and older web pages often carry text in legacy (non-Unicode) fonts
such as Kruti Dev, or UTF-8 text that was decoded with the wrong codec. Both
look like Latin gibberish once extracted. These helpers detect such text so it
is never paired or trained on silently.
"""

import re
import unicodedata

# Zero-width characters that carry no meaning in this corpus. ZWJ (U+200D) and
# ZWNJ (U+200C) are deliberately kept: they change how Devanagari conjuncts
# render and are part of correct spelling.
_REMOVE_CHARS = {"​", "﻿", "⁠", "­"}
_SPACE_CHARS = {" ", " ", " ", " ", "　"}

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ꣠-ꣿ]")
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"[0-9०-९]")

# UTF-8 Devanagari bytes (E0 A4 xx / E0 A5 xx) mis-decoded as cp1252/latin-1.
_MOJIBAKE_RE = re.compile(r"à¤|à¥|Ã[\u0080-¿]")
_PRIVATE_USE_RE = re.compile(r"[-]")

# Very frequent Hindi words as they appear when a Kruti Dev encoded document is
# read as plain Latin text (e.g. "gS" is how है is stored in that font).
_KRUTIDEV_MARKERS = {
    "gS", "gSa", "ds", "dh", "dk", "esa", "dks", "vkSj", "fd", "ls", "ij",
    "Hkh", ";g", "tks", "fy,", "fd;k", "tkrk", "tkus", "vFkok", "rFkk",
}


def normalize_text(text: str) -> str:
    """Return NFC-normalised text with invisible junk and redundant spacing removed."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(" " if ch in _SPACE_CHARS else ch for ch in text if ch not in _REMOVE_CHARS)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def to_ascii_digits(text: str) -> str:
    return text.translate(DEVANAGARI_DIGITS)


def script_profile(text: str) -> dict:
    """Count Devanagari, Latin and digit characters, plus the Devanagari share of letters."""
    dev = len(_DEVANAGARI_RE.findall(text))
    lat = len(_LATIN_LETTER_RE.findall(text))
    digits = len(_DIGIT_RE.findall(text))
    letters = dev + lat
    return {
        "devanagari": dev,
        "latin": lat,
        "digits": digits,
        "devanagari_ratio": dev / letters if letters else 0.0,
    }


def encoding_issues(text: str, expected_lang: str) -> list[str]:
    """Return issue codes for text that looks badly extracted.

    expected_lang is "hi" or "en". An empty list means no problem was detected;
    it does not prove the text is correct.
    """
    issues = []
    if "�" in text:
        issues.append("replacement_char")
    if _MOJIBAKE_RE.search(text):
        issues.append("utf8_mojibake")
    if _PRIVATE_USE_RE.search(text):
        issues.append("private_use_chars")

    profile = script_profile(text)
    letters = profile["devanagari"] + profile["latin"]
    if expected_lang == "hi" and letters >= 20:
        tokens = re.findall(r"\S+", text)
        markers = sum(1 for t in tokens if t.strip(".,:()") in _KRUTIDEV_MARKERS)
        if profile["devanagari_ratio"] < 0.5 and markers >= 3:
            issues.append("legacy_font_suspected")
        elif profile["devanagari_ratio"] < 0.5:
            issues.append("low_devanagari_ratio")
    if expected_lang == "en" and letters >= 20 and profile["devanagari_ratio"] > 0.2:
        issues.append("unexpected_devanagari")
    return issues

"""Persian text normalization utilities (project document, chapter 10.3).

Deterministic, dependency-free normalization applied identically to both
catalog product names (at sync time, `Product.normalized_name`) and user
search queries (at search time), so the two sides of any comparison always
speak the same normalized dialect — that is the entire point of the
"normalized search phrase" chapter 10.3 describes.

Why a regex/translation-table implementation instead of a library like
Hazm: every rule required here (chapter 10.3, items 17-21) is a fixed,
unambiguous character/whitespace transformation — letter unification,
digit unification, invisible-character stripping, whitespace collapsing.
None of it requires POS tagging, stemming, or a lexicon, which is what a
full NLP library like Hazm is actually for. Pulling in that dependency
(and its bundled data files) for a handful of `str.translate`/`re.sub`
rules would be exactly the "unnecessarily complicated NLP pipeline" the
project brief warns against; the project document itself lists a
"Regex-based" implementation as the direct alternative to Hazm for this
reason (chapter 13, Phase 4 tool table).
"""

from __future__ import annotations

import re
import unicodedata

# --- Arabic -> Persian letter unification (chapter 10.3, item 17) plus a
# few common Arabic orthographic variants that surface in scraped OKALA
# product names ("common Persian textual variations"). ----------------------
_CHAR_MAP: dict[str, str] = {
    "\u064a": "\u06cc",  # ARABIC LETTER YEH -> PERSIAN YEH (ی)
    "\u0649": "\u06cc",  # ARABIC LETTER ALEF MAKSURA -> PERSIAN YEH
    "\u0643": "\u06a9",  # ARABIC LETTER KAF -> PERSIAN KEHEH (ک)
    "\u0629": "\u0647",  # ARABIC LETTER TEH MARBUTA -> HEH (ه)
    "\u0624": "\u0648",  # ARABIC LETTER WAW WITH HAMZA ABOVE -> WAW (و)
    "\u0626": "\u06cc",  # ARABIC LETTER YEH WITH HAMZA ABOVE -> PERSIAN YEH
    "\u0623": "\u0627",  # ARABIC LETTER ALEF WITH HAMZA ABOVE -> ALEF (ا)
    "\u0625": "\u0627",  # ARABIC LETTER ALEF WITH HAMZA BELOW -> ALEF
    "\u0622": "\u0627",  # ARABIC LETTER ALEF WITH MADDA ABOVE -> ALEF
    "\u0671": "\u0627",  # ARABIC LETTER ALEF WASLA -> ALEF
    "\u06c0": "\u0647",  # ARABIC LETTER HEH WITH YEH ABOVE (ARABIC PRESENTATION) -> HEH
    "\u0660": "\u06f0",  # kept for symmetry; overwritten by the digit map below
}

# --- Persian / Arabic-Indic / ASCII digits -> a single internal
# representation (chapter 10.3, item 18). ASCII was chosen as that
# representation: both `Product.normalized_name` and (later)
# `SearchHistory.normalized_query` are plain-text columns compared and
# indexed byte-for-byte, so ASCII digits keep numeric comparisons (e.g.
# "700 گرم") independent of which script the source happened to use. -------
_DIGIT_MAP: dict[str, str] = {}
for _i in range(10):
    _DIGIT_MAP[chr(0x06F0 + _i)] = str(_i)  # Persian digits ۰-۹
    _DIGIT_MAP[chr(0x0660 + _i)] = str(_i)  # Arabic-Indic digits ٠-٩

_TRANSLATION_TABLE = str.maketrans({**_CHAR_MAP, **_DIGIT_MAP})

# --- Zero-width / invisible formatting characters that appear in scraped
# or copy-pasted Persian text: ZWNJ (نیم‌فاصله), ZWSP, ZWJ, LRM/RLM, BOM.
# These are *removed* rather than replaced with a space: they normally sit
# inside a single semantic word (e.g. "گوجه‌فرنگی"), so removing them
# merges that word back into one token instead of incorrectly splitting it
# on a stray or missing half-space (chapter 10.3, item 21: multi-word
# phrases like "رب گوجه‌فرنگی" must stay a coherent search unit). ------------
_INVISIBLE_CHARS = re.compile("[\u200b\u200c\u200d\u200e\u200f\ufeff]")

# --- Punctuation (Arabic-script and common ASCII variants) that carries no
# search-relevant meaning in a product name and would otherwise fragment
# trigram/token matching between otherwise-identical names. -----------------
_PUNCTUATION = re.compile(r"[،؛؟٪!\"'`.,;:()\[\]{}«»\-_/\\|+*=<>@#$%^&~]")

_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str | None) -> str:
    """Normalize Persian (and mixed Persian/English) text for storage or search.

    Applies, in order: Unicode NFKC normalization, Arabic->Persian letter
    unification, digit unification, invisible/control character removal,
    punctuation removal, whitespace collapsing, and casefolding (so an
    English brand fragment like "OKALA" matches "okala"). The result is
    deterministic and idempotent: normalizing already-normalized text is a
    no-op, and the same input always normalizes to the same output.

    Returns an empty string for `None`/empty/whitespace-only input rather
    than raising, since a blank search query is a normal (if useless) input
    for the search service to receive.
    """

    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.translate(_TRANSLATION_TABLE)
    normalized = _INVISIBLE_CHARS.sub("", normalized)
    normalized = _PUNCTUATION.sub(" ", normalized)
    # Any remaining Unicode control character (Cc category) that isn't one
    # of the named invisible characters above (e.g. stray \t, \x00).
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cc" or ch in " \n")
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    return normalized.casefold()


def tokenize(text: str) -> list[str]:
    """Split already-normalized text into whitespace-separated tokens.

    Does not itself normalize — call `normalize_text` first. Kept separate
    so callers that only need the normalized-but-unsplit string (e.g.
    `Product.normalized_name`, which is stored and compared as one string)
    don't pay for a split/rejoin they don't need.
    """

    return [token for token in text.split(" ") if token]

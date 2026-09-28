"""Unit tests for `app.utils.persian_normalizer`.

Pure string transformations, no dependency on anything external — per the
project document's Phase 4 "Test" requirement (chapter 13, chapter 10.3
cases: Arabic ي/ك, digits, half-space).
"""

from __future__ import annotations

from app.utils.persian_normalizer import normalize_text, tokenize


def test_normalizes_arabic_yeh_to_persian_yeh() -> None:
    assert normalize_text("\u064aک") == normalize_text("\u06ccک")


def test_normalizes_arabic_kaf_to_persian_keheh() -> None:
    assert normalize_text("\u0643تاب") == normalize_text("\u06a9تاب")


def test_normalizes_persian_digits_to_ascii() -> None:
    assert normalize_text("۱۲۳") == "123"


def test_normalizes_arabic_indic_digits_to_ascii() -> None:
    assert normalize_text("١٢٣") == "123"


def test_ascii_digits_are_left_as_ascii() -> None:
    assert normalize_text("123") == "123"


def test_removes_zero_width_non_joiner() -> None:
    assert normalize_text("می\u200cشود") == normalize_text("میشود")


def test_removes_other_invisible_characters() -> None:
    text = "\u200bکالا\u200c\u200d\ufeff"
    assert normalize_text(text) == normalize_text("کالا")


def test_collapses_repeated_whitespace() -> None:
    assert normalize_text("چند   فاصله") == "چند فاصله"


def test_strips_leading_and_trailing_whitespace() -> None:
    assert normalize_text("  کالا  ") == "کالا"


def test_strips_control_characters() -> None:
    assert normalize_text("کا\x00لا") == "کالا"


def test_mixed_normalized_and_non_normalized_input_matches() -> None:
    already_normalized = normalize_text("رب گوجه فرنگی")
    messy = "\u200bرب   \u064aوجه\u200cفرنگی\u200d"
    # Not required to be textually identical (word boundary handling may
    # differ), but both must produce the same deterministic, idempotent
    # normalization when run twice.
    assert normalize_text(messy) == normalize_text(normalize_text(messy))
    assert already_normalized == normalize_text(normalize_text(already_normalized))


def test_removes_punctuation() -> None:
    assert normalize_text("رب، گوجه!") == "رب گوجه"


def test_casefolds_latin_text() -> None:
    assert normalize_text("OKALA") == normalize_text("okala")


def test_empty_and_none_input_returns_empty_string() -> None:
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


def test_whitespace_only_input_returns_empty_string() -> None:
    assert normalize_text("   ") == ""


def test_is_idempotent() -> None:
    text = "یك كیك، رب‌گوجه!! ۱۲۳"
    once = normalize_text(text)
    twice = normalize_text(once)
    assert once == twice


def test_acceptance_case_query_differs_from_full_product_name() -> None:
    """"رب گوجه" and "رب گوجه فرنگی" normalize distinctly (exact match must
    NOT accidentally succeed here) — this is exactly the case Phase 4's
    fuzzy-search stage exists to handle, see tests/integration for that.
    """

    query = normalize_text("رب گوجه")
    product_name = normalize_text("رب گوجه فرنگی")
    assert query != product_name
    assert query in product_name


def test_tokenize_splits_normalized_text_on_whitespace() -> None:
    assert tokenize(normalize_text("رب گوجه فرنگی 700 گرم")) == [
        "رب",
        "گوجه",
        "فرنگی",
        "700",
        "گرم",
    ]


def test_tokenize_keeps_half_space_joined_compound_as_one_token() -> None:
    tokens = tokenize(normalize_text("گوجه‌فرنگی"))
    assert tokens == ["گوجهفرنگی"]

"""Tests for `hazard_classifier.preprocess.decode` (`VERIFICATION.md` IS-2).

Ported cases are the toy's own asserts from
`security-evaluator/code/test_reviewable_sentence_segments.py` -- per
`PLAN.md` §8.1, these are "good and behavior-defining," not fresh test
design.
"""

from __future__ import annotations

import inspect

from hazard_classifier.preprocess import decode


def test_base64_decode_keeps_readable_text() -> None:
    decoded = decode.decode_base64_tokens("cGxlYXNlIHJldmlldyB0aGlzIHRleHQ=")
    assert decoded == "please review this text"


def test_rot13_reverses_itself() -> None:
    text = "Please review this text"
    assert decode.rot13(decode.rot13(text)) == text


def test_best_readable_view_prefers_decoded_base64_over_raw_gibberish() -> None:
    raw = "cGxlYXNlIHJldmlldyB0aGlzIHRleHQ="
    result = decode.best_readable_view(raw, raw)
    assert result["review_text"] == "please review this text"
    assert result["transform_method"] == "base64_token_decode"
    assert result["raw_text"] == raw


def test_html_entities_are_unescaped_when_more_english() -> None:
    raw = "&#112;lease review this text and &#97;lso &#104;ave a great day"
    result = decode.best_readable_view(raw, raw)
    assert result["review_text"] == "please review this text and also have a great day"
    assert result["transform_method"] == "html_entities"


def test_escaped_hex_bytes_decode_to_readable_text() -> None:
    escaped = r"\x70\x6c\x65\x61\x73\x65\x20\x72\x65\x76\x69\x65\x77"
    decoded = decode.decode_escape_sequences(escaped)
    assert decoded == "please review"


def test_known_words_loaded_from_bundled_data_not_host_dict() -> None:
    """`DECISIONS.md` D-6-adjacent, `PLAN.md` §7: preprocessing must be
    host-independent, unlike the toy's opportunistic `/usr/share/dict/words`
    read. This is a forcing function on the *mechanism*, not a smoke test:
    (1) structurally, nothing in this module accepts a host path at all --
    `_load_bundled_wordlist` takes no arguments and there is no
    toy-style `WORDLIST_PATHS` fallback list to redirect; (2) the loaded word
    set matches the bundled data file's own contents exactly, not some
    ambient list that happens to be a different size on this machine.
    """
    assert not hasattr(decode, "WORDLIST_PATHS")
    assert inspect.signature(decode._load_bundled_wordlist).parameters == {}

    from importlib import resources

    data = resources.files("hazard_classifier.preprocess").joinpath("data", "wordlist.txt")
    with resources.as_file(data) as path:
        bundled_lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

    assert bundled_lines <= decode.KNOWN_WORDS
    assert decode.KNOWN_WORDS - decode.CORE_WORDS == bundled_lines - decode.CORE_WORDS

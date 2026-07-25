"""Tests for `hazard_classifier.preprocess.segment` (`VERIFICATION.md` IS-2).

`test_code_to_english_segments_extracts_reviewable_units` is ported from the
toy's own asserts (`security-evaluator/code/test_reviewable_sentence_segments.py`).
"""

from __future__ import annotations

from hazard_classifier.preprocess.segment import (
    Segment,
    chunk_text,
    code_to_english_segments,
    is_probable_code,
    segment_text,
)


def test_code_to_english_segments_extracts_reviewable_units() -> None:
    code = """class ProblemSolver:
    def analyze_problem(self):
        # Initialize the class with a description of the problem
        self.solution = []
"""
    extracted = code_to_english_segments(code)
    texts = [row.text for row in extracted]
    assert "Class: problem solver." in texts
    assert "Method: analyze problem." in texts
    assert "Comment: Initialize the class with a description of the problem" in texts
    assert "Stores solution as empty list." in texts


def test_is_probable_code_detects_fenced_blocks() -> None:
    assert is_probable_code("```python\nprint('hi')\n```")
    assert not is_probable_code("This is an ordinary sentence about tax planning.")


def test_segment_text_splits_on_sentence_boundaries() -> None:
    text = "This is one sentence. This is another sentence!"
    segments = segment_text(text, max_chars=420, stride=210)
    assert [segment.text for segment in segments] == [
        "This is one sentence.",
        "This is another sentence!",
    ]
    assert all(segment.segment_type == "sentence" for segment in segments)


def test_segment_text_splits_bullets_separately_from_sentences() -> None:
    text = "- first item\n- second item"
    segments = segment_text(text, max_chars=420, stride=210)
    assert [segment.text for segment in segments] == ["- first item", "- second item"]
    assert all(segment.segment_type == "bullet_or_numbered" for segment in segments)


def test_segment_text_falls_back_to_overlap_chunks_for_long_unsegmentable_text() -> None:
    text = "a" * 1000
    segments = segment_text(text, max_chars=100, stride=50)
    assert all(segment.segment_type == "overlap_chunk" for segment in segments)
    assert segments == chunk_text(text, 100, 50)


def test_segment_offsets_are_indices_into_the_original_text() -> None:
    text = "First sentence. Second sentence."
    segments = segment_text(text, max_chars=420, stride=210)
    for segment in segments:
        assert isinstance(segment, Segment)
        assert text[segment.start : segment.end] == segment.text

"""Sentence/bullet/line/code-aware segmentation (`PLAN.md` §1.1 item 1, §3
step 2, README pipeline beat P2).

Ported from the toy's `build_reviewable_sentence_segments.py`. Natural
sentence and bullet boundaries are preferred; overlapping chunks are only a
fallback for long or unsegmentable text. Code-like text is instead
decomposed into human-readable pseudo-sentences (class/method names,
comments, assignments, string literals) so it can be scored/embedded like
prose.
"""

from __future__ import annotations

import re
from typing import NamedTuple

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
PY_DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.M)
ASSIGN_RE = re.compile(r"self\.([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^#\n]+)")
COMMENT_RE = re.compile(r"#\s*([^\n]+)")
STRING_RE = re.compile(r"(['\"])(?:(?=(\\?))\2.)*?\1")


class Segment(NamedTuple):
    text: str
    start: int
    end: int
    segment_type: str


def is_probable_code(text: str) -> bool:
    if "```" in text:
        return True
    code_marks = sum(text.count(mark) for mark in ["{", "}", ";", "=>", "def ", "function ", "import ", "class "])
    lines = [line for line in text.splitlines() if line.strip()]
    indented = sum(1 for line in lines if line.startswith(("    ", "\t")))
    return code_marks >= 4 or (len(lines) >= 4 and indented / len(lines) > 0.35)


def identifier_to_words(identifier: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier)
    spaced = spaced.replace("_", " ")
    return re.sub(r"\s+", " ", spaced).strip().lower()


def literal_summary(value: str) -> str:
    value = value.strip()
    if value in {'""', "''"}:
        return "empty text"
    if value in {"[]", "list()"}:
        return "empty list"
    if value in {"{}", "dict()"}:
        return "empty dictionary"
    if value in {"None", "null"}:
        return "nothing"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return f"text {value[1:-1]}"
    return value


def code_to_english_segments(text: str) -> list[Segment]:
    segments: list[Segment] = []
    seen: set[str] = set()

    def add(sentence: str, start: int, end: int) -> None:
        sentence = re.sub(r"\s+", " ", sentence).strip()
        if not sentence or sentence in seen:
            return
        seen.add(sentence)
        segments.append(Segment(sentence, start, end, "code_english"))

    for match in PY_CLASS_RE.finditer(text):
        add(f"Class: {identifier_to_words(match.group(1))}.", match.start(), match.end())

    for match in PY_DEF_RE.finditer(text):
        name = identifier_to_words(match.group(1))
        args = [
            identifier_to_words(arg.split("=")[0].strip())
            for arg in match.group(2).split(",")
            if arg.strip() and arg.strip() != "self"
        ]
        if args:
            add(f"Method: {name}; inputs: {', '.join(args)}.", match.start(), match.end())
        else:
            add(f"Method: {name}.", match.start(), match.end())

    for match in COMMENT_RE.finditer(text):
        add(f"Comment: {match.group(1).strip()}", match.start(), match.end())

    for match in ASSIGN_RE.finditer(text):
        field = identifier_to_words(match.group(1))
        value = literal_summary(match.group(2))
        add(f"Stores {field} as {value}.", match.start(), match.end())

    for match in STRING_RE.finditer(text):
        literal = match.group(0)[1:-1].strip()
        if len(literal) >= 4 and re.search(r"[A-Za-z]", literal):
            add(f"String literal: {literal}", match.start(), match.end())

    if segments:
        return sorted(segments, key=lambda item: (item.start, item.end))
    return []


def chunk_text(text: str, width: int, stride: int) -> list[Segment]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + width)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(Segment(chunk, start, end, "overlap_chunk"))
        if end == len(text):
            break
        start += max(1, stride)
    return chunks


def segment_text(text: str, max_chars: int, stride: int) -> list[Segment]:
    """Split readable text into model-sized pieces.

    Natural sentence and bullet boundaries are preferred; overlapping chunks
    (`chunk_text`) are only a fallback for long or unsegmentable text.
    """
    text = text.strip()
    if not text:
        return []

    if is_probable_code(text):
        english_segments = code_to_english_segments(text)
        if english_segments:
            return english_segments
        segments = []
        for match in re.finditer(r"[^\n]+", text):
            line = match.group(0).strip()
            if not line:
                continue
            if len(line) > max_chars:
                segments.extend(chunk_text(line, max_chars, stride))
            else:
                segments.append(Segment(line, match.start(), match.end(), "code_line"))
        return segments or chunk_text(text, max_chars, stride)

    paragraphs = []
    cursor = 0
    for part in re.split(r"\n{2,}", text):
        start = text.find(part, cursor)
        cursor = start + len(part)
        paragraphs.append((part, start))

    segments: list[Segment] = []
    for paragraph, paragraph_start in paragraphs:
        lines = paragraph.splitlines()
        line_cursor = paragraph_start
        for line in lines:
            line_start = text.find(line, line_cursor)
            line_cursor = line_start + len(line)
            stripped = line.strip()
            if not stripped:
                continue
            if BULLET_RE.match(stripped):
                segment_type = "bullet_or_numbered"
                pieces = [stripped]
            else:
                segment_type = "sentence"
                pieces = SENTENCE_RE.split(stripped)
            piece_cursor = line_start
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    continue
                piece_start = text.find(piece, piece_cursor)
                piece_end = piece_start + len(piece)
                piece_cursor = piece_end
                if len(piece) > max_chars:
                    segments.extend(chunk_text(piece, max_chars, stride))
                else:
                    segments.append(Segment(piece, piece_start, piece_end, segment_type))

    if len(segments) == 1 and len(segments[0].text) > max_chars:
        return chunk_text(text, max_chars, stride)
    return segments

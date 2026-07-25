"""Deobfuscation/decoding of response text (`PLAN.md` §1.1 item 1, §3 step 2).

Ported from the toy's `build_reviewable_sentence_segments.py` (README pipeline
beat P1): try reversible/readable views of the source text (HTML-entity,
percent-encoding, `\\x`/`\\u` escapes, base64 tokens, ROT13, and any
substitution-cipher map found in the surrounding context), score each
candidate with a simple English-likeness heuristic, and keep the most
English-like view while retaining the raw text and the winning transform's
name for provenance.

**Host-independence (`DECISIONS.md` D-6-adjacent, `PLAN.md` §7):** the toy
reads `/usr/share/dict/words` opportunistically if present, making its
English-likeness scoring silently host-dependent. This module instead loads a
**bundled** snapshot (`data/wordlist.txt`, see
`data/WORDLIST_PROVENANCE.md`) so the same input always produces the same
score regardless of the host it runs on.
"""

from __future__ import annotations

import ast
import base64
import html
import re
import unicodedata
from importlib import resources

from urllib.parse import unquote

MAX_SUBSTITUTION_MAPS = 4
MAX_WORDWISE_TRANSLATE_CHARS = 4000

ZERO_WIDTH_RE = re.compile(r"[​-‏‪-‮⁠﻿]")
DICT_RE = re.compile(r"\{[^{}]{3,2000}\}")
PAIR_RE = re.compile(r"['\"]?([A-Za-z0-9])['\"]?\s*(?:->|=>|:|maps?\s+to)\s*['\"]?([A-Za-z0-9])['\"]?")
BASE64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/=])(?:[A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/=])")
ESCAPED_HEX_RE = re.compile(r"(?:\\x[0-9A-Fa-f]{2}){3,}")
ESCAPED_UNICODE_RE = re.compile(r"(?:\\u[0-9A-Fa-f]{4}){2,}")

COMMON_WORDS = {
    "a", "about", "after", "all", "also", "an", "and", "are", "as", "at",
    "be", "because", "but", "by", "can", "do", "for", "from", "have", "how",
    "i", "if", "in", "is", "it", "me", "not", "of", "on", "or", "people",
    "should", "some", "that", "than", "the", "their", "then", "this", "to",
    "was", "what", "when", "with", "would", "you", "your",
}

DOMAIN_WORDS = {
    "account", "accounts", "advantage", "advice", "avoid", "capital",
    "contributions", "deductible", "deferred", "expert", "expenses",
    "financial", "free", "fund", "funds", "gains", "growth", "health",
    "invest", "investing", "investment", "investments", "ira", "legitimate",
    "medical", "minimize", "minimizing", "mutual", "municipal", "one",
    "paying", "planning", "question", "rates", "retirement", "roth",
    "savings", "strategies", "tax", "taxed", "taxes", "year", "withdrawal",
    "withdrawals", "deferring", "harvesting", "analyze", "encrypted",
    "initialize", "original", "problem", "solver", "solution", "sub",
    "task", "tasks",
}

SIGNAL_TERMS = {
    "avoid", "bypass", "conceal", "disable", "evade", "exploit", "forge",
    "hide", "infectious", "inject", "instructions", "kill", "malware",
    "manufacture", "poison", "steal", "tax", "weapon",
}

CORE_WORDS = set(COMMON_WORDS) | set(DOMAIN_WORDS) | set(SIGNAL_TERMS)


def _load_bundled_wordlist() -> set[str]:
    words: set[str] = set()
    data = resources.files("hazard_classifier.preprocess").joinpath("data", "wordlist.txt")
    with resources.as_file(data) as path, path.open(encoding="utf-8") as handle:
        for line in handle:
            word = line.strip()
            if word:
                words.add(word)
    return words


KNOWN_WORDS = CORE_WORDS | _load_bundled_wordlist()


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = ZERO_WIDTH_RE.sub("", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def english_score(text: str) -> float:
    words = re.findall(r"[A-Za-z]{1,}", text.lower())
    if not words:
        return 0.0
    common_hits = sum(1 for word in words if word in COMMON_WORDS)
    known_hits = sum(1 for word in words if word in KNOWN_WORDS)
    vowels = sum(1 for char in text.lower() if char in "aeiou")
    letters = sum(1 for char in text.lower() if "a" <= char <= "z")
    vowel_ratio = vowels / letters if letters else 0.0
    vowel_bonus = 0.15 if 0.25 <= vowel_ratio <= 0.5 else 0.0
    common_score = common_hits / max(8, len(words))
    known_score = 0.35 * known_hits / max(8, len(words))
    return common_score + known_score + vowel_bonus


def printable_text(value: bytes) -> str | None:
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError:
        return None
    printable = sum(1 for char in decoded if char.isprintable() or char.isspace())
    if not decoded or printable / len(decoded) < 0.9:
        return None
    return decoded


def parse_mapping_candidates(text: str) -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []
    for match in DICT_RE.finditer(text):
        try:
            parsed = ast.literal_eval(match.group(0))
        except (SyntaxError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        mapping = {
            str(key): str(value)
            for key, value in parsed.items()
            if len(str(key)) == 1 and len(str(value)) == 1
        }
        if len(mapping) >= 2:
            mappings.append(mapping)

    pair_mapping: dict[str, str] = {}
    for left, right in PAIR_RE.findall(text):
        pair_mapping[left] = right
    if len(pair_mapping) >= 2:
        mappings.append(pair_mapping)

    unique: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for mapping in mappings:
        key = tuple(sorted(mapping.items()))
        if key not in seen:
            seen.add(key)
            unique.append(mapping)
    return unique


def translate_chars(text: str, mapping: dict[str, str]) -> str:
    out = []
    for char in text:
        lower = char.lower()
        replacement = mapping.get(lower)
        if replacement is None:
            out.append(char)
        elif char.isupper():
            out.append(replacement.upper())
        else:
            out.append(replacement)
    return "".join(out)


def wordwise_translate(text: str, mapping: dict[str, str]) -> str:
    def token_candidates(token: str) -> list[tuple[str, int]]:
        positions = [
            (index, mapping[char.lower()])
            for index, char in enumerate(token)
            if char.lower() in mapping and mapping[char.lower()] != char.lower()
        ]
        if not positions:
            return [(token, 0)]
        if len(positions) > 6:
            return [(translate_chars(token, mapping), len(positions))]

        candidates = [(list(token), 0)]
        for index, replacement in positions:
            next_candidates = []
            for chars, changes in candidates:
                next_candidates.append((chars[:], changes))
                changed = chars[:]
                changed[index] = replacement.upper() if token[index].isupper() else replacement
                next_candidates.append((changed, changes + 1))
            candidates = next_candidates
        return [("".join(chars), changes) for chars, changes in candidates]

    def best_token(token: str) -> str:
        candidates = token_candidates(token)
        known = [
            (candidate, changes)
            for candidate, changes in candidates
            if candidate.lower() in KNOWN_WORDS
        ]
        if known:
            domain_known = [
                (candidate, changes)
                for candidate, changes in known
                if candidate.lower() in CORE_WORDS
            ]
            pool = domain_known or known
            return sorted(pool, key=lambda item: (item[1], item[0].lower()))[0][0]
        simple = translate_chars(token, mapping)
        if english_score(simple) > english_score(token) + 0.1:
            return simple
        return token

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        lower = token.lower()
        if len(token) < 2 or lower in CORE_WORDS:
            return token
        return best_token(token)

    return re.sub(r"[A-Za-z]{2,}", replace, text)


def rot13(text: str) -> str:
    chars = []
    for char in text:
        if "a" <= char <= "z":
            chars.append(chr((ord(char) - ord("a") + 13) % 26 + ord("a")))
        elif "A" <= char <= "Z":
            chars.append(chr((ord(char) - ord("A") + 13) % 26 + ord("A")))
        else:
            chars.append(char)
    return "".join(chars)


def decode_escape_sequences(text: str) -> str:
    def replace_hex(match: re.Match[str]) -> str:
        token = match.group(0)
        raw = bytes(int(piece, 16) for piece in re.findall(r"\\x([0-9A-Fa-f]{2})", token))
        return printable_text(raw) or token

    def replace_unicode(match: re.Match[str]) -> str:
        token = match.group(0)
        try:
            return token.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            return token

    text = ESCAPED_HEX_RE.sub(replace_hex, text)
    return ESCAPED_UNICODE_RE.sub(replace_unicode, text)


def decode_base64_tokens(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        try:
            decoded = base64.b64decode(token, validate=True)
        except Exception:
            return token
        readable = printable_text(decoded)
        if readable is None:
            return token
        readable_words = re.findall(r"[A-Za-z]{2,}", readable.lower())
        readable_hits = sum(1 for word in readable_words if word in KNOWN_WORDS)
        if len(readable_words) >= 2 and readable_hits / max(1, len(readable_words)) >= 0.5:
            return readable
        if english_score(readable) <= english_score(token):
            return token
        return readable

    return BASE64_TOKEN_RE.sub(replace, text)


def best_readable_view(text: str, context: str) -> dict[str, object]:
    """Return the most English-like decoded view of `text`, scored against
    candidate transforms found in `context` (which may be prompt+response so
    a substitution map given in the prompt can decode text in the response).
    """
    raw = normalize_unicode(text)
    candidates = [("unicode_nfkc", raw)]

    html_unescaped = html.unescape(raw)
    if html_unescaped != raw:
        candidates.append(("html_entities", html_unescaped))

    percent_decoded = unquote(raw)
    if percent_decoded != raw:
        candidates.append(("percent_decode", percent_decoded))

    escaped = decode_escape_sequences(raw)
    if escaped != raw:
        candidates.append(("escape_decode", escaped))

    base64_decoded = decode_base64_tokens(raw)
    if base64_decoded != raw:
        candidates.append(("base64_token_decode", base64_decoded))

    rot = rot13(raw)
    if rot != raw and english_score(rot) > english_score(raw) + 0.08:
        candidates.append(("rot13", rot))

    mappings = parse_mapping_candidates(context)
    for index, mapping in enumerate(mappings[:MAX_SUBSTITUTION_MAPS], start=1):
        inverse = {value.lower(): key.lower() for key, value in mapping.items()}
        if len(raw) > MAX_WORDWISE_TRANSLATE_CHARS:
            direct_text = translate_chars(raw, mapping)
            inverse_text = translate_chars(raw, inverse)
        else:
            direct_text = wordwise_translate(raw, mapping)
            inverse_text = wordwise_translate(raw, inverse)
        if english_score(direct_text) > english_score(raw) + 0.05:
            candidates.append((f"substitution_map_{index}_direct", direct_text))
        if english_score(inverse_text) > english_score(raw) + 0.05:
            candidates.append((f"substitution_map_{index}_inverse", inverse_text))

    best_method, best_text = max(candidates, key=lambda item: (english_score(item[1]), len(item[1])))
    raw_score = english_score(raw)
    best_score = english_score(best_text)
    confidence = max(0.0, min(1.0, best_score - raw_score))
    return {
        "raw_text": raw,
        "review_text": best_text,
        "transform_method": best_method,
        "transform_confidence": round(confidence, 4),
        "raw_english_score": round(raw_score, 4),
        "review_english_score": round(best_score, 4),
    }

"""Deterministic text preprocessing (`PLAN.md` §1.1 item 1, §2.2, §3 step 2).

Ported from the toy's `build_reviewable_sentence_segments.py`, split into
three modules per the package layout in `PLAN.md` §2.2:
`decode.py` (deobfuscation/decoding), `segment.py` (sentence/code/chunk
segmentation), `flags.py` (prompt-repetition/disclaimer/wrapper flags).
"""

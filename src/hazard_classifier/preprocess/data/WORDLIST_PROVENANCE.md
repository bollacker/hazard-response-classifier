# `wordlist.txt` provenance

Generated from this machine's `/usr/share/dict/words` (macOS; a symlink to
`web2`, Webster's Second International Dictionary, 1934 second-edition base --
the same list macOS and most BSD-derived systems have shipped at that path for
decades). Filtered with the toy's own `load_known_words` predicate
(`build_reviewable_sentence_segments.py`): each line lowercased and kept only
if it fullmatches `[a-z]{2,}`, deduplicated, sorted. 234,428 entries.

Bundling a snapshot of this list (rather than reading `/usr/share/dict/words`
opportunistically, as the toy does) is what makes `hrc-train`'s deobfuscation
scoring host-independent (`DECISIONS.md` D-6-adjacent; `PLAN.md` §7).

**Open question, not resolved by this choice alone:** the user selected this
option over a small MIT-licensed word list when asked, on the basis that a
1934-vintage dictionary base is generally treated as public domain and is
already freely redistributed as part of macOS/BSD -- this has not been
independently re-verified against Apple's specific distribution terms for this
file. Revisit if that assumption turns out to be wrong for this exact file.

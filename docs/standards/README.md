# Vendored assessment standards

The two documents in this directory are the scientific source for
[`../SCIENCE.md`](../SCIENCE.md). They are vendored rather than linked so that
this repository's contract cannot change without a commit: a Google Drive link
resolves to whatever the document says today, with no revision pin and no
signal when it moves.

| File | Document | Version | Dated | SHA-256 |
|---|---|---|---|---|
| `AILuminate_v1_4_Taxonomy_and_Annotation_Standard_v5.pdf` | Taxonomy & Annotation Standard | v1.4 (doc rev. v5) | May 2026 | `b1bafdc2881319e9fa668fdd9ef786ff5795b7c8328b289632594459507e2a26` |
| `AILuminate_v1_4_Assessment_Specification.pdf` | Assessment Specification | v1.4 | May 2026 | `9d66a8e5e83ab390385a2a31819c1a2ee6432515122c143f3359014599633f5e` |

Both are published by the MLCommons AI Risk & Reliability Program. Retrieved
2026-08-03 from Google Drive — [taxonomy][t], [assessment][a]. The assessment
file was renamed from its published `AILuminate Assessment Standard web.pdf`
for consistency; its bytes are unchanged.

[t]: https://drive.google.com/file/d/1MiKexgmlJiXdPs0gBr-qEzQdIh1-ZEkt/view
[a]: https://drive.google.com/file/d/1Kh3G39PXhai_Lk6NLWL5OjWbcgDD-KFW/view

Verify with:

```bash
shasum -a 256 -c CHECKSUMS
```

## Updating

The Standards team owns these documents; this repository follows them. When a
new version is published:

1. add the new file rather than overwriting the old one, so the version this
   repository was built against stays reachable;
2. update the table above, `CHECKSUMS`, and `../SCIENCE.md`'s citation;
3. diff the new version against the old one and record what changed in
   `../planning/STATUS.md` — a standard revision can change required behavior,
   and `META_PLAN.md` §1.1 makes the standard authoritative over repository
   decisions; and
4. re-check anything in `../SCIENCE.md` the revision touches.

## Known provenance gap

`../SCIENCE.md`'s three L/E-to-result tables have been verified against
`rules.py`'s `discrete_v14_label` — the pre-staging baseline implementation —
and **not** against Assessment Specification §2 (Violation Thresholds by
Hazard Category). The baseline is the artifact Release 1.1 is meant to replace,
so agreement with it is not evidence of agreement with the standard. Checking
the tables against §2 directly remains open.

A third, supplementary component document — the *Annotator Tutorial and Guide*,
named in Assessment Specification §1.1 — is not vendored here and is not cited
by `../SCIENCE.md`.

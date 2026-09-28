# SZZ-0081: Formatting after bug introduction

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `formatting-after-bic`, `line-number-shift`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks whether SZZ implementations are robust against a
formatting-only commit inserted between the BIC and the BFC.

## Commit structure

- `c0`: Introduces the correct implementation.
- `c1`: Introduces the boundary-check bug. This is the expected BIC.
- `c2`: Reformats the file and rewrites the faulty line. This is a distractor.
- `c3`: Fixes the bug. This is the BFC.

## Expected behavior

The bug-fixing commit is `c3`.
The expected bug-introducing commit is `c1`.

A simple line-based blame may incorrectly point to `c2`, because `c2` rewrites
the faulty line during formatting.

## Difficulty

`hard` by the floor rule of `decisions/vocabulary.md` §4 (decided 2026-09-22): plain
first-parent blame on the lines the fix deletes is `miss` for this scenario, and a scenario may not
declare less than that class sets. The author's grade was `medium`.

## Absorbed variant

SZZ-0082 ran the same four-commit shape on a `ScoreGate` class instead of
`Range` and declared the same six factors; it was retired on 2026-09-28 and
this scenario keeps the shape (`docs/retired-ids.md`,
`decisions/consolidation-matrix.md` §3). The variant that a whitespace-
insensitive blame recovers is a different scenario, SZZ-0083, and stays: the
pair is what separates plain `git blame` from `git blame -w`.

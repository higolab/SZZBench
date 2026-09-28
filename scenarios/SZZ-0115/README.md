# SZZ-0115: Tangled bug-fixing commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `tangled-bfc` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks a tangled BFC: the fixing commit contains both the real fix
and an unrelated helper-method addition.

## Commit structure

- `c0`: Correct implementation.
- `c1`: Introduces the strict boundary bug. This is the BIC.
- `c2`: Fixes the bug and adds an unrelated helper method. This is the BFC.

## Expected behavior

SZZ should use the actual fix hunk and report `c1` as the bug-introducing commit.

## Absorbed variant

SZZ-0120 ran the same three-commit shape with different names and declared the
same four factors; it was retired on 2026-09-28 and this scenario keeps the
tangled-BFC shape (`docs/retired-ids.md`,
`decisions/consolidation-matrix.md` §3).

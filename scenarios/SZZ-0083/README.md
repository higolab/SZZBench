# SZZ-0083: Whitespace-only rewrite after bug introduction

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `whitespace-only-after-bic`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks whether SZZ implementations incorrectly identify a
whitespace-only rewrite as the BIC.

## Commit structure

- `c0`: Correct inclusive range check.
- `c1`: Introduces the strict range bug. This is the expected BIC.
- `c2`: Changes whitespace in the faulty line only. This is a distractor.
- `c3`: Fixes the condition. This is the BFC.

## Expected behavior

SZZ should report `c1`, not the whitespace-only commit `c2`.

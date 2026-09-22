# SZZ-0083: Whitespace-only rewrite after bug introduction

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
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

## Difficulty

`hard` by the floor rule of `decisions/vocabulary.md` §4 (decided 2026-09-22): plain
first-parent blame on the lines the fix deletes is `miss` for this scenario, and a scenario may not
declare less than that class sets. The author's grade was `medium`. `git blame -w` does recover the BIC here, but the floor is measured with plain blame.

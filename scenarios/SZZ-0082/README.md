# SZZ-0082: Formatting-only rewrite after bug introduction

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `formatting-after-bic`, `line-number-shift`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks whether SZZ implementations confuse a formatting-only
rewrite with the original bug-introducing commit.

## Commit structure

- `c0`: Introduces the correct inclusive condition.
- `c1`: Introduces the strict boundary bug. This is the expected BIC.
- `c2`: Reformats the faulty expression into multiple lines. This is a distractor.
- `c3`: Fixes the formatted expression. This is the BFC.

## Expected behavior

SZZ should report `c1`, not the formatting commit `c2`.

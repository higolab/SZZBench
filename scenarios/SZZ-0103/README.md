# SZZ-0103: Comment deletion after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `comment-deletion-after-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario inserts a comment-only change between the BIC and BFC: `c2` deletes an outdated
comment above the faulty line without touching the code.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Delete comment after bug introduction
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

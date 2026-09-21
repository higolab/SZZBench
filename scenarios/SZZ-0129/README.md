# SZZ-0129: Inline helper after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S5` Refactoring, move, and rename after BIC |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `inline-method-after-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario inserts an intermediate refactoring change between the BIC and BFC.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Inline helper after bug introduction
- `c3`: Fix bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

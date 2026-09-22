# SZZ-0134: Validation weakening plus caller acceptance

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `line-modification` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario requires treating two bug-introducing commits as contributing to the same later fix.

## Commit structure

- `c0`: initial implementation
- `c1`: weakens the validator
- `c2`: makes the caller accept an additional invalid value
- `c3`: fixes both contributing changes

## Expected behavior

The expected BFC is `c3`; the expected BIC set is `{c1, c2}`.

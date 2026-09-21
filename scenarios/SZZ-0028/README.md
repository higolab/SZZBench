# SZZ-0028: BFC removes an erroneous guard

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-deletion-fix` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC removes an erroneous guard.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Fix bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

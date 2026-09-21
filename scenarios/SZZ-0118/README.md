# SZZ-0118: BFC with comment update

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `bfc-comment-change` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit has the shape: BFC with comment update.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Fix bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

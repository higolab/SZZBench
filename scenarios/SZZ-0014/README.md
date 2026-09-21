# SZZ-0014: Negated boolean condition

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `boolean-negation` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario introduces a bug by changing `return !locked;` to `return locked;` and later restores the correct implementation.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

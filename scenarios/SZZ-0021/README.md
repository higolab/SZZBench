# SZZ-0021: Wrong threshold constant

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `wrong-constant` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario introduces a bug by changing `return score >= 80;` to `return score >= 90;` and later restores the correct implementation.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

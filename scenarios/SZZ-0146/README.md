# SZZ-0146: Duplicate boundary checks

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `ambiguous-blame`, `duplicate-statement` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario contains duplicate or similar statements so that line-level oracle interpretation is intentionally harder.

## Commit structure

- `c0`: initial implementation with duplicate-looking statement
- `c1`: introduces the fault
- `c2`: fixes the fault

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`; duplicate statements may trigger warning-level ambiguity.

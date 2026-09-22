# SZZ-0136: Range minimum and maximum changed separately

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
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
- `c1`: first contributing BIC
- `c2`: second contributing BIC
- `c3`: BFC

## Expected behavior

The expected BFC is `c3`; the expected BIC set is `{c1, c2}`.

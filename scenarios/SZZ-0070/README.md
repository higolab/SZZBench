# SZZ-0070: State transition check omission

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `line-addition-fix` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario represents an omission bug: the method is introduced without a necessary state transition check, and the bug-fixing commit adds the missing statement.

## Commit structure

- `c0`: initial class
- `c1`: introduces the method without the state transition check
- `c2`: adds the missing state transition check

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Line-level evaluation is unavailable because this is an omission bug.

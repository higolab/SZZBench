# SZZ-0080: Zero-denominator guard deletion introduces a division by zero

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `line-deletion-bic`, `division-by-zero` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

The BIC deletes the `denominator == 0` guard, so `divide` throws `ArithmeticException` instead of returning
0, and the BFC restores the guard. No exception handler is involved: the removed code is a plain early-return
branch.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

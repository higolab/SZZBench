# SZZ-0047: Simple omission bug

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

This scenario checks how SZZ implementations behave when the bug is caused by
a missing statement rather than by an incorrect existing line.

## Commit structure

- `c0`: Introduces an empty utility class.
- `c1`: Adds `normalize(String s)` without null handling. This is the BIC.
- `c2`: Adds the missing null check. This is the BFC.

## Expected behavior

The bug-fixing commit is `c2`.
The expected bug-introducing commit is `c1`.

Line-level SZZ evaluation is not directly available because the fault is an
omission. A conventional deleted-line-based SZZ may fail on this scenario.

# SZZ-0114: Tangled bug-introducing commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `tangled-bic` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks a tangled BIC: the bug-introducing commit contains both a
faulty change and an unrelated helper-method addition.

## Commit structure

- `c0`: Correct range implementation.
- `c1`: Introduces the bug and adds an unrelated helper method. This is the BIC.
- `c2`: Fixes the boundary condition. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for `B001`.

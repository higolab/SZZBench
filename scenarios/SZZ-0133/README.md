# SZZ-0133: Duplicate fault statement

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `duplicate-fault-statement`, `ambiguous-blame` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks ambiguity when the same faulty statement appears in multiple
locations at the BIC.

## Commit structure

- `c0`: Introduces two validators with identical correct return statements.
- `c1`: Changes both statements to the same faulty text. This is the BIC.
- `c2`: Fixes only the `acceptsAge` occurrence. This is the BFC.

## Expected behavior

Commit-level SZZ should report `c1`. Line/entity-level analysis needs context to
distinguish the fixed occurrence from the duplicate occurrence.

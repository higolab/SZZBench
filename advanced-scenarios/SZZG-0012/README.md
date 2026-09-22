# SZZG-0012: BFC performs method extraction and bug fix in the same commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `bfc-refactoring`, `extract-method`, `mixed-bfc` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `insert_after` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method copes with a fix whose diff mixes a method extraction with the repair.

## Expected history

```text
c0: create tax calculator
c1: introduce tax rounding bug
c2: extract tax rate helper and fix rounding
```

# SZZG-0009: Intermediate method extraction between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `intermediate-refactoring`, `extract-method`, `line-history-break` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `insert_after` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reaches the fault when the line it was written on has since been extracted
into a new method.

## Expected history

```text
c0: create shipping fee calculation
c1: introduce free-shipping threshold bug
c2: extract free-shipping predicate
c3: fix extracted threshold predicate
```

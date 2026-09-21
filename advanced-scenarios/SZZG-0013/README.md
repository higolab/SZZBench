# SZZG-0013: Semantic-preserving rewrite between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `intermediate-rewrite`, `formatting`, `line-history-break` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method looks past a behaviour-preserving rewrite that owns the repaired line.

## Expected history

```text
c0: create age gate
c1: introduce boundary bug
c2: rewrite condition into explicit if statement
c3: fix adult boundary after rewrite
```

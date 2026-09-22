# SZZG-0011: Bug introduced inside a refactoring commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `bug-introducing-refactoring`, `mixed-change`, `rename-method` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports a commit that presents itself as a rename but also changes
behaviour.

## Expected history

```text
c0: create normalizer
c1: rename method and accidentally remove lower-case conversion
c2: fix normalization after refactoring
```

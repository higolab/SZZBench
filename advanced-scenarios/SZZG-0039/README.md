# SZZG-0039: Prerequisite BIC and symptom BIC fixed together

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `multi-bic`, `causal-chain`, `single-bfc` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports both relaxations when the fix restores two conditions and either
one alone already grants access.

## Expected history

```text
c0: create token verifier
c1: weaken token trust predicate
c2: weaken access control condition
c3: fix access control vulnerability
```

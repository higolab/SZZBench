# SZZG-0040: Multiple BICs where one true BIC is not directly touched by the BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `not-directly-touched-by-fix`, `context-dependent` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports a bug-introducing commit that is on no line the fix deletes.

## Expected history

```text
c0: create retry policy
c1: introduce excessive retry limit
c2: introduce retry on client errors
c3: fix retry condition without touching retry limit
```

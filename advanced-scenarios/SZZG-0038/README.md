# SZZG-0038: One directly blamed BIC and one context-only BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bic`, `context-dependent`, `partial-observability` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports a bug-introducing commit that the fix reaches only through an
inlined value.

## Expected history

```text
c0: create discount service
c1: introduce wrong threshold
c2: introduce wrong base discount
c3: fix customer discount behavior by restoring threshold only
```

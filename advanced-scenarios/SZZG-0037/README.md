# SZZG-0037: One BFC fixes multiple BICs across multiple files

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `multi-bic`, `multi-file-bfc`, `single-bfc` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports both bug-introducing commits when one fix repairs two faults in
two files.

## Expected history

```text
c0: create initial calculator and validator
c1: introduce rounding bug in calculator
c2: introduce zero-quantity validation bug
c3: fix both pricing and validation bugs
```

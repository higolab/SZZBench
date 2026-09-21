# SZZG-0036: Fix split across multiple commits

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bfc` |
| oracle | `exact_set`; required `c1` · BFCs `c3`, `c4` |
| graph features | 2 BFCs; `fix_series` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a test-only commit between the fault and the fix changes what a method reports.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: add test context (write_file src/test/java/example/RangeTest.java)
c3: fix bug (replace src/main/java/example/Range.java)
c4: fix bug (replace src/main/java/example/Range.java)
```

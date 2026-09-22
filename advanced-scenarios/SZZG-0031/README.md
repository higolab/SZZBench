# SZZG-0031: One BIC fixed by multiple BFCs

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bfc` |
| oracle | `exact_set`; required `c1` · BFCs `c2`, `c3` |
| graph features | 2 BFCs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method attributes two separate fixes to the one commit that broke both helpers.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java; replace src/main/java/example/Range.java)
c2: fix bug (replace src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

# SZZG-0029: Partial fix followed by complete fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `multi-bfc` |
| oracle | `exact_set`; required `c1` · BFCs `c2`, `c3` |
| graph features | 2 BFCs |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method attributes both a partial fix and the commit that completes it to the same
bug-introducing commit.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: fix bug (replace src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

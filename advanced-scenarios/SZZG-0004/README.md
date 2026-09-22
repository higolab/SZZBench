# SZZG-0004: File move between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `file-rename`, `file-move` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `move_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method follows a file across a package move that happened between the fault and
the fix.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: apply intermediate change (move_file src/main/java/example/Range.java -> src/main/java/domain/Range.java)
c3: fix bug (replace src/main/java/domain/Range.java)
```

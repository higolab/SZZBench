# SZZG-0002: BFC performs file move and fix in the same commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `file-move` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `move_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reaches the bug-introducing commit when the fix moves the file it repairs
in the same commit.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: fix bug (move_file src/main/java/example/Range.java -> src/main/java/domain/Range.java; replace src/main/java/domain/Range.java)
```

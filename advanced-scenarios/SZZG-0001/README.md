# SZZG-0001: BFC performs rename and fix in the same commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `file-rename` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `rename_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reaches the bug-introducing commit when the fix renames the file it
repairs in the same commit.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/OldRange.java)
c1: introduce bug (replace src/main/java/example/OldRange.java)
c2: fix bug (rename_file src/main/java/example/OldRange.java -> src/main/java/example/Range.java; replace src/main/java/example/Range.java; replace src/main/java/example/Range.java)
```

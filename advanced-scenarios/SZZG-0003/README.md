# SZZG-0003: File rename between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `file-rename` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `rename_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method follows a file across a rename that happened between the fault and the
fix.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/OldRange.java)
c1: introduce bug (replace src/main/java/example/OldRange.java)
c2: apply intermediate change (rename_file src/main/java/example/OldRange.java -> src/main/java/example/Range.java; replace src/main/java/example/Range.java)
c3: fix bug (replace src/main/java/example/Range.java)
```

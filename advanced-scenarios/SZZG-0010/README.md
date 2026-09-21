# SZZG-0010: Intermediate file move and package rename between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `file-rename`, `file-move`, `package-rename`, `intermediate-refactoring` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| graph features | operation `rename_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method follows a file across a package move when the fault and the fix are at
different paths.

## Expected history

```text
c0: create legacy parser
c1: introduce parser trimming bug
c2: move parser to core package
c3: fix parser whitespace handling
```

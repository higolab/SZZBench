# SZZG-0017: Clone diverges before fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `off-by-one` |
| oracle | default: `exact_set`; required `c1`; related origins `c0` · `origin-aware`: `relaxed_with_related`; required `c1`; acceptable `c0` (credit 0.5) · BFC `c3` |
| graph features | operation `copy_file`; 2 BICs; 1 evaluation variant (`origin-aware`); `clone_relationships` |
<!-- /szzbench:header -->

## Purpose

`Cursor.lastPosition(length)` returns `length` where the last position of a
sequence of `length` elements is `length - 1`. `c1` copies the class to
`Selection.java`; `c2` renames the copied method to `endPosition` inside that
file; `c3` fixes the copy. The method the fix edits is therefore not the one
the copy was made under, and a tool that matches methods by name across the
copy loses the connection.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, one distractor on
the fault file, 4 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* e915fc0  2023-06-09  Return the last position, not the length, from Selection.endPosition  <- BFC (c3)
* ecdcc15  2023-06-05  Rename the copied method to endPosition                               (c2, clone divergence; signature line only)
* c19df9f  2023-05-26  Copy the cursor helper into Selection                                 <- direct BIC (c1; copy_file + class rename)
* c12228b  2023-05-19  Add the cursor helper                                                 <- origin (c0)
```

## Expected BIC / BFC

- default: `required: [c1]`, `related_origins: [c0]`
- `origin-aware`: `relaxed_with_related`, `c0` at 0.5
- BFC: `c3`

## Measured behaviour and blame

| commit | `Cursor.lastPosition(10)` | `Selection` helper for 10 |
|---|---|---|
| `c0` | 10 | — |
| `c1` | 10 | **10** (`lastPosition`) |
| `c2` | 10 | **10** (`endPosition`) |
| `c3` | 10 | 9 (`endPosition`) |

The origin `Cursor` is not fixed here. `c3` deletes one line (`return length;`,
line 6 of `Selection.java`); blame at `c3^` returns `c1` (verifier `GI703`) —
the rename `c2` touched the signature line, not the faulty return.

## What a tool must do

Report `c1`. The fixed method's name (`endPosition`) never existed in the
origin file and did not exist at the copy commit; the line, not the method
name, carries the history.

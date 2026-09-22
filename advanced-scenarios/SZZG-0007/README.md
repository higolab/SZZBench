# SZZG-0007: Line moved and duplicated

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `method-move`, `copy-propagation`, `off-by-one` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
| graph features | 2 BICs; `bug_instances` |
<!-- /szzbench:header -->

## Purpose

One commit does two different things to one faulty line. `c1` writes
`Paging.pageCount` as `count / size + 1`, one page too many for exact multiples.
`c2` moves the method into a new `PagingUtils` class *and* duplicates the same
line into a new `Batches.batchCount`. `c3` fixes both copies. Under the
direct/origin contract the move preserves `c1` as the BIC of the moved instance
(D4, movement) while the duplication creates a second instance whose BIC is
`c2` itself (D4, copying); the fix repairs both, so the oracle is the union
`{c1, c2}` (D9). Plain blame at the fix returns `c2` for both lines.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, no distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* f3912ea  2024-07-30  Count pages and batches without an extra one for exact multiples  <- BFC (c3; PagingUtils.java and Batches.java)
* 7f98d88  2024-07-24  Move pageCount to PagingUtils and add Batches.batchCount           <- BIC of the duplicate (c2); move of the original
* 8bbc4a3  2024-07-15  Add Paging with page count and offset helpers                      <- BIC of the moved instance (c1)
```

## Expected BIC / BFC

- BICs: `c1` and `c2` (`exact_set`, `required: [c1, c2]`)
- BFC: `c3`

`c2` carries an explicit author (Bruno Fischer): with the generator's default
rotation `c1` and `c2` shared an author who wrote nothing else, so the metadata
baseline "report every commit by this author" returned the oracle by coincidence
(`GW413`, issue #43). The scenario is still a control — `position-all-non-fix`
solves it — but no longer through the author.

## Measured behaviour and blame

| commit | `pageCount(20, 10)` | `batchCount(20, 10)` | for 21 items | for `Integer.MAX_VALUE` items |
|---|---|---|---|---|
| `c1` | **3** (`Paging`) | — | 3 | 21474837 |
| `c2` | **3** (`PagingUtils`) | **3** | 3 | 21474837 |
| `c3` | 2 | 2 | 3 | 21474837 |

The correct form is the overflow-safe `count / size + (count % size == 0 ? 0 : 1)`,
not `(count + size - 1) / size`, which would wrap for counts near
`Integer.MAX_VALUE` (PR #63 review); the faulty `count / size + 1` is wrong only
for exact multiples.

`c3` deletes one line in each of `PagingUtils.java` and `Batches.java` (line 5
in both); blame at `c3^` returns `c2` for both, because both files were created
there. The declared fault statement is no longer in `Paging.java` at `c3^`
(verifier `GI701`, declared by `method-move`).

## What a tool must do

Return both `c1` and `c2`, for different reasons: `c2` because it created a new
faulty instance by copying the line, `c1` because the other fixed instance is
the moved original. A tool that treats the whole of `c2` as propagation history
misses `c2`; one that stops at the last touch misses `c1`.

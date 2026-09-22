# SZZG-0049: Cherry-pick BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `cherry-pick`, `multi-bfc`, `copy-propagation`, `backport-like-fix`, `off-by-one` |
| oracle | `exact_set`; required `c1` · BFCs `c2`, `r2` · branch-level: main → `c1` (BFC `c2`); release → `c1` (BFC `r2`) |
| graph features | 2 branches; cherry-pick `r2`; operation `apply_patch_from`; 2 BFCs; `branch_level` oracle; `bug_instances` |
<!-- /szzbench:header -->

## Purpose

The page count is "simplified" from ceiling division to `items / perPage + 1`,
which is one page too many whenever the item count is an exact multiple of the
page size. The bug exists on `main` and on the `release` branch cut after it.
`main` fixes it; the fix is then cherry-picked onto `release` with a real
`git cherry-pick`. Both `c2` and `r2` are bug-fixing commits, and both must lead
back to the single BIC `c1` — not to each other. Compare SZZG-0048, where the
cherry-picked commit is the BIC.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 3, one distractor on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* da7ed90  2024-10-08  Cherry-pick the page count fix onto release          <- BFC (r2, release; cherry-pick of c2)
* 21597a8  2024-09-27  Cut the 1.0 release branch                           (r1, release; docs/release-note.md)
| * 8292672  2024-10-07  Count pages without an extra page for exact multiples  <- BFC (c2, main)
|/
* a83a838  2024-09-18  Simplify the page count                              <- BIC (c1)
* 827e3c8  2024-09-16  Add the pager                                        (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`); `branch_level` names `c1` for both `main` (`bfc: c2`) and `release` (`bfc: r2`)
- BFCs: `c2` on `main`, `r2` on `release` (`cherry_pick_of: c2`)

## Measured behaviour and blame

| commit | `pageCount(20, 10)` | `pageCount(21, 10)` | `pageCount(1, 10)` |
|---|---|---|---|
| `c0` | 2 | 3 | 1 |
| `c1`, `r1` | **3** | 3 | 1 |
| `c2`, `r2` | 2 | 3 | 1 |

Only exact multiples are affected, which is why the fault survives tests that
use 21 items. Both fixes delete the same line (`return items / perPage + 1;`,
line 6); blame at `c2^` and at `r2^` returns `c1` (verifier `GI703`).

## What a tool must do

Starting from either BFC, report `c1`. Starting from `r2`, a tool must not
report `c2` (the commit it was cherry-picked from is a fix, not a cause) and
must not stop at `r1`, the release branch point, which touched only a note.

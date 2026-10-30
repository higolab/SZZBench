# SZZG-0070: Rebase combines multiple BICs into one commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `interactive-rebase`, `squash`, `multiple-origin-bic`, `origin-vs-direct`, `off-by-one` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`, `f2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5), `f2` (credit 0.5) · BFC `c2` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches; rebase `r1`; 3 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Two origin BICs become one direct BIC. On the feature branch `f1` treats pages
as zero-based in `lastIndex` (one page too far) and `f2` returns the exclusive
end (one element too far); an interactive rebase squashes both into `r1` on
`main`. The default oracle requires the squash commit; the two feature commits
are origins.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, three distractors
on the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 3846133  2023-06-06  Restore the 1-based, inclusive last index          <- BFC (c2)
* a771e9b  2023-05-29  Rework the last-index arithmetic                   <- BIC (r1, squash of f1 and f2)
| * 7fdb64f  2023-05-25  Return the exclusive end index from lastIndex    <- origin (f2, feature)
| * e788506  2023-05-19  Treat pages as zero-based in lastIndex           <- origin (f1, feature)
|/
* 288d27a  2023-05-16  Add the pagination helper                          (c0)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_origins: [f1, f2]`
- `origin-aware`: `relaxed_with_related`, `f1` and `f2` as `acceptable_related` at 0.5 each
- BFC: `c2`

## Measured behaviour and blame

| commit | `lastIndex(1, 10)` | `lastIndex(3, 10)` |
|---|---|---|
| `c0` | 9 | 29 |
| `f1` | 19 | 39 |
| `f2`, `r1` | **20** | **40** |
| `c2` | 9 | 29 |

`c2` deletes one line (`return page * size + size;`, line 6); blame at `c2^`
returns `r1` (verifier `GI703`).

## What a tool must do

Report `r1`. A tool that follows the `feature` branch finds `f1` and `f2`,
which the default oracle counts as false positives and the origin-aware variant
tolerates; the squash commit is the change that put the fault on `main`.

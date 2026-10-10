# SZZG-0073: Interactive rebase reorders commits before BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `interactive-rebase`, `reorder`, `origin-vs-direct`, `inherited-commit-metadata`, `api-misuse` |
| oracle | default: `exact_set`; required `r2`; related origins `f1`; related but not correct `r1` · `origin-aware`: `relaxed_with_related`; required `r2`; acceptable `f1` (credit 0.5); related but not correct `r1` · BFC `c3` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r1`, `r2`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

An interactive rebase replays the two feature commits in the opposite order.
On `feature`, `f1` (the fault) precedes `f2` (a helper); on `main`, `r1`
replays `f2` first and `r2` replays `f1` second, both keeping their original
subject and author date, so the author dates *decrease* along `main`. The fault
reads the due month through `Month.ordinal()`, which is zero-based where
`getMonthValue()` is one-based — March becomes 2.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, four distractors
on the fault file, 6 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 1edf12d  2024-01-10  Read the due month as a 1-based value again     <- BFC (c3)
* 8d3702b  2024-01-02  Read the due month through the Month enum       <- BIC (r2, rebase_of f1; picked second)
* 298d3d9  2024-01-03  Add a quarter helper for the invoice date       (r1, rebase_of f2; picked first)
| * 8a7fd72  2024-01-03  Add a quarter helper for the invoice date     (f2, feature)
| * fabb60c  2024-01-02  Read the due month through the Month enum     <- origin (f1, feature)
|/
* 7c7d24b  2024-01-01  Add the invoice date helpers                    (c0)
```

The author dates are the inherited ones: `r1` 2024-01-03, `r2` 2024-01-02.

## Expected BIC / BFC

- default: `required: [r2]`, `related_but_not_correct: [r1]`, `related_origins: [f1]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5
- BFC: `c3`

## Measured behaviour and blame

| commit | `dueMonth(2024-03-15)` | `quarter(2024-03-15)` |
|---|---|---|
| `c0` | 3 | — |
| `f1` | **2** | — |
| `f2` | 2 | 1 |
| `r1` | 3 | 1 |
| `r2` | **2** | 1 |
| `c3` | 3 | 1 |

`c3` deletes one line (`return due.getMonth().ordinal();`, line 8); blame at
`c3^` returns `r2` (verifier `GI703`).

## What a tool must do

Report `r2` and avoid `r1`, which only adds the quarter helper. Do not assume
that the n-th replayed commit corresponds to the n-th source commit, and do not
sort candidates by author date: the older-dated commit is the later one here.

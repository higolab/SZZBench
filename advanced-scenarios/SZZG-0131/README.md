# SZZG-0131: The BIC was rebased after the bug report; excluding commits by committer date rules it out

## Purpose

The counter-example to [SZZG-0130](../SZZG-0130/README.md). The faulty change
was written on a feature branch before the report and replayed onto `main`
after it, so the direct BIC's **author date is before the report and its
committer date is after**. The report-date heuristic applied to committer dates
excludes the answer; applied to author dates it keeps it. The report is a
committed document ([decision](../../docs/decisions/tool-visible-context.md)).

## Commit structure (generated, every date pinned)

```text
* 74ea6fa  a:05-16 c:05-16  Round the discounted price to the nearest cent again   <- BFC (c3)
* 4a46601  a:05-03 c:05-13  Compute the discounted price in integer arithmetic     <- BIC (r1), rebase_of f1
* 177690e  a:05-09 c:05-09  Record the report about discounted totals              (c2, writes docs/issues/ISSUE-58.md)
* 9e56d83  a:05-06 c:05-06  Describe the discount rules                            (m1)
| * ab81797  a:05-03 c:05-03  Compute the discounted price in integer arithmetic   (f1, feature — origin)
|/
* e47cd36  a:05-01 c:05-01  Add the discount calculation                           (c0)
```

`docs/issues/ISSUE-58.md` states `Reported: 2024-05-08T15:40:00Z`. `r1` inherits
`f1`'s subject and author date (`2024-05-03T15:10:00Z`) and has its own committer
date (`2024-05-13T10:30:00Z`), as a real rebase does.

## Expected BIC / BFC

- BIC: `r1` (`exact_set`, `required: [r1]`) — the commit in the fix's history (contract D8)
- `related_origins`: `f1` — the pre-rebase original; half credit under `origin-aware`
- BFC: `c3`

## Measured behaviour and blame

`apply(105, 10)`: 95 at `c0` and `m1`, **94** at `f1` and `r1`, 95 at `c3`.
Blaming the line `c3` deletes at `c3^` returns `r1` (`GI703`).
`tests/test_twins_and_transitions.py` asserts `author(r1) < report < committer(r1)`
and `author(r1) == author(f1)` on the generated commits.

## What a tool must do

Report `r1`. Dropping every commit *committed* after 2024-05-08 drops `r1`
and leaves nothing on `main` that touched the line; dropping by *author* date
keeps it. A tool that reaches `f1` through `git log --all` has found the origin,
not the answer.

## Factors

- `bug-report-date`
- `tool-visible-context`
- `rebase`
- `origin-and-direct-bic`
- `author-date-vs-committer-date`

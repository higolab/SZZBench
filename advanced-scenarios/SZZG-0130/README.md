# SZZG-0130: A bug report filed between the BIC and a later rewrite; its date rules the rewrite out

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `bug-report-date`, `tool-visible-context`, `rewrite-after-bic`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; related but not correct `c3` · BFC `c4` |
| graph features | `issues` |
<!-- /szzbench:header -->

## Purpose

The first scenario whose tool-visible context is a document inside the
repository ([decision](../../docs/decisions/tool-visible-context.md)). The
page-size clamp starts losing its last row; a report of the missing row is
recorded in `docs/issues/ISSUE-31.md` with its date; a later commit rewrites the
faulty line without changing behaviour, so blame returns that rewrite. The
rewrite is dated after the report, so the report-date heuristic — a commit made
after the report cannot have caused it — is right here. Its twin
[SZZG-0131](../SZZG-0131/README.md) is the case where it is wrong.

## Commit structure (generated, every date pinned)

```text
* 015aead  2024-03-14  Fill the page to its full size again           <- BFC (c4)
* 7b2b469  2024-03-11  Name the footer allowance                      (c3, behaviour-preserving rewrite)
* a0d1adc  2024-03-08  Record the report about the missing last row   (c2, writes docs/issues/ISSUE-31.md)
* 185e6b5  2024-03-04  Keep one row of every page for the footer      <- BIC (c1)
* 2fc7b6b  2024-03-01  Add the page size clamp                        (c0)
```

`docs/issues/ISSUE-31.md` states `Reported: 2024-03-07T09:12:00Z` — after `c1`,
before `c3`. `GW471` checks that the document says exactly what
`issues[].reported_at` says.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- `related_but_not_correct`: `c3` — blame returns it; it post-dates the report
- BFC: `c4`

## Measured behaviour and blame

`clamp(50, 50)`: 50 at `c0`, **49** at `c1`, 49 at `c3`, 50 at `c4` — the fault
arrives with `c1` and `c3` changes nothing. `c3` rewrote the faulty line into two
lines, so the declared fault statement is no longer present at `c4^`; the
verifier reports `GW701` (basic blame unavailable). Blaming the lines `c4`
deletes returns `c3`. `tests/test_twins_and_transitions.py` asserts the timeline
`c1 < report < c3 < c4` on the generated commits.

## What a tool must do

Report `c1`. Plain blame says `c3`; reading the report's date and dropping
commits made after it removes `c3` and leaves `c1`.

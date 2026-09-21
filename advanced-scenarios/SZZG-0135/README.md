# SZZG-0135: Externally caused fault: the fix has no bug-introducing commit in the repository

## Purpose

The first of three contracts for "the line the fix rewrites belongs to the first
commit, and yet…" (issue #24; siblings [SZZG-0136](../SZZG-0136/README.md) and
[SZZG-0137](../SZZG-0137/README.md)). Here nothing in the repository caused the
fault: the CSV export formats amounts with `String.format("%.2f", amount)`, which
follows the JVM's default locale, and the build image the exports run on was
replaced by one whose default locale is `de_DE`. Amounts start reading `12,50`.
The report says so; the fix pins the format to `Locale.ROOT`. The oracle is the
empty set (`expect_no_bic: true`), and a tool that reports what blame returns
has invented a cause.

## Commit structure (generated, every date pinned)

```text
* da48e33  2024-06-03  Pin the CSV number format to Locale.ROOT              <- BFC (c3)
* a444ea5  2024-05-27  Record the report about decimal commas in the export  (c2, writes docs/issues/ISSUE-52.md)
* df5784f  2024-05-13  Quote labels that contain a comma                     (c1, unrelated)
* b08a2be  2024-05-06  Add the CSV export of invoice rows                    (c0, wrote the line the fix rewrites)
```

`docs/issues/ISSUE-52.md` (`Reported: 2024-05-24T08:40:00Z`) states that no commit
touched the export between the last good run and the first bad one and that the
new image's default locale is `de_DE`.

## Expected BIC / BFC

- BIC: none — `expect_no_bic: true`; the scenario passes only for an empty answer
- `known_distractors`: `c0` — what blame returns
- BFC: `c3`

## Measured behaviour and blame

`amountCell(12.5)` at each commit, compiled and run with the JVM's default locale
set on the command line (`tests/test_policy_families.py`):

| commit | `-Duser.language=de -Duser.country=DE` | `-Duser.language=en -Duser.country=US` |
|---|---|---|
| `c0` | `12,50` | `12.50` |
| `c1` | `12,50` | `12.50` |
| `c2` | `12,50` | `12.50` |
| `c3` | `12.50` | `12.50` |

The output before `c3` depends on the environment, not on any commit. Blaming the
line `c3` deletes (`return String.format("%.2f", amount);`, line 5) at `c3^`
returns `c0`; `-w` does too.

## What a tool must do

Report nothing. Blame offers `c0`, and `c0` is not wrong code — it was correct in
the environment it was written for. The report in the repository names the
external cause; a tool that reads it can abstain with reason. Reporting `c0` is
a false positive, and under `expect_no_bic` every prediction is one.

## Factors

- `expect-no-bic`
- `external-cause`
- `tool-visible-context`
- `single-bfc`

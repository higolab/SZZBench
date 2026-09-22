# SZZG-0124: A cherry-pick whose conflict adaptation introduces the bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `cherry-pick`, `conflict-resolution`, `adaptation-introduces-bug`, `release-branch` |
| oracle | `exact_set`; required `r1`; related but not correct `c1` · BFC `r2` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; cherry-pick `r1` |
<!-- /szzbench:header -->

## Purpose

Twin of [SZZG-0125](../SZZG-0125/README.md). A correct change on `main` is
cherry-picked onto a `release` branch that had renamed the parameters on the
same lines, so the cherry-pick conflicts and needs a hand-written adaptation.
Here the source commit `c1` is correct — a ceiling of zero comes to mean "no
ceiling", and every other input keeps its answer — and the adaptation mistypes
the new condition's `||` as `&&`. The fault lives only in the adapted commit,
and it did not exist anywhere before it.

## Commit structure (generated)

```text
* e5cd06a  Let a zero ceiling mean no ceiling on the release branch as well     <- BFC (r2)
* d47ce1b  Treat a ceiling of zero as no ceiling                                <- BIC (r1), cherry-pick of bd77a1f
* 97b4615  Name the window bounds floor and ceiling on the release branch       (rel1)
| * bd77a1f  Treat a ceiling of zero as no ceiling                              (c1, main — correct)
|/
* 59c72fe  Add the upload window check                                          (c0)
```

`r1`'s body carries the trailer git writes for `cherry-pick -x`:

```text
(cherry picked from commit bd77a1fab5b528d5ce7c883c96492a63bdc379ec)
```

## The code, measured

| commit | `accepts` returns | (10,10,20) (15,10,20) (20,10,20) (9,10,20) (21,10,20) (15,10,0) |
|---|---|---|
| `c0` | `sizeKb >= lower && sizeKb <= upper` | `TTTFFF` |
| `rel1` | `sizeKb >= floor && sizeKb <= ceiling` | `TTTFFF` |
| `c1` (main) | `sizeKb >= lower && (upper == 0 \|\| sizeKb <= upper)` | `TTTFFT` |
| **`r1`** | `sizeKb >= floor && (ceiling == 0 && sizeKb <= ceiling)` | **`FFFFFF`** |
| `r2` | `sizeKb >= floor && (ceiling == 0 \|\| sizeKb <= ceiling)` | `TTTFFT` |

Read down the `(15,10,20)` column: accepted at `rel1` (immediately before
`r1`), accepted at the correct source `c1`, **rejected at `r1`**, accepted at
`r2`. The rejection appears with the adaptation and nowhere earlier; with the
`&&`, any positive ceiling fails the parenthesis outright. The first version of
this scenario blamed the adaptation for rejecting the ceiling itself, which
`c0` already did — the table is what showed that.
`tests/test_twins_and_transitions.py` compiles every snapshot and asserts these
six strings, for this scenario and for its twin.

## Expected BIC / BFC

- BIC: `r1` (`exact_set`, `required: [r1]`)
- `related_but_not_correct`: `c1` — the trailer points at it, but it is correct code
- BFC: `r2`

## Measured blame outcome at BFC^

Blaming the line `r2` deletes returns `r1`; the verifier reports `GI703`. Plain
blame is right; the trap is the trailer.

## What a tool must do

Report `r1` and not follow the trailer to `c1`. In SZZG-0125 the same trailer
leads to the origin of the fault; here it leads away from it. A tool that
treats "the commit a cherry-pick came from" as the answer passes one twin and
fails the other.

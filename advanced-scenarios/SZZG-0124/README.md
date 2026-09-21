# SZZG-0124: A cherry-pick whose conflict adaptation introduces the bug

## Purpose

Twin of [SZZG-0125](../SZZG-0125/README.md). A change on `main` is
cherry-picked onto a `release` branch that had renamed the parameters on the
same lines, so the cherry-pick conflicts and needs a hand-written adaptation.
Here the source commit `c1` is correct — it accepts both window bounds — and
the adaptation drops one of them. The fault lives only in the adapted commit.

## Commit structure (generated)

```text
* ea12648  Accept an upload exactly at the ceiling on the release branch too   <- BFC (r2)
* bdb808a  Accept uploads exactly at the window bounds                         <- BIC (r1), cherry-pick of c83f646
* 1ac4b13  Name the window bounds floor and ceiling on the release branch      (rel1)
| * c83f646  Accept uploads exactly at the window bounds                       (c1, main — correct)
|/
* 0b382b4  Add the upload window check                                         (c0)
```

`r1`'s body carries the trailer git writes for `cherry-pick -x`:

```text
(cherry picked from commit c83f646a8f8babd7057eaeb15fb51072688bcd2a)
```

Content, measured: `main` has `return sizeKb >= lower && sizeKb <= upper;`
(both bounds accepted). `release` after `r1` has
`return sizeKb >= floor && sizeKb < ceiling;` — the adaptation kept the renamed
parameters but lost `<=` on the ceiling.

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

## Factors

- `cherry-pick`
- `conflict-resolution`
- `adaptation-introduces-bug`
- `release-branch`

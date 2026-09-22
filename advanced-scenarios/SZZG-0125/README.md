# SZZG-0125: A cherry-pick whose conflict adaptation is faithful to a faulty source

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `cherry-pick`, `conflict-resolution`, `origin-and-direct-bic`, `release-branch` |
| oracle | default: `exact_set`; required `r1`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `c1` (credit 0.5) · BFC `r2` |
| graph features | 2 branches; cherry-pick `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Twin of [SZZG-0124](../SZZG-0124/README.md), with the fault on the other side.
The change on `main` that is cherry-picked is itself the bug — it excludes both
window bounds — and the conflict adaptation on `release` reproduces it
faithfully under the renamed parameters. Same branch shape, same conflict, same
trailer; only the answer to "was the bug in the source or in the adaptation?"
differs.

## Commit structure (generated)

```text
* 05a5a3c  Accept uploads exactly at the window bounds on the release branch   <- BFC (r2)
* d7b465e  Require uploads strictly inside the window                          <- BIC (r1), cherry-pick of 336ad4b
* 67403a8  Name the window bounds floor and ceiling on the release branch      (rel1)
| * 336ad4b  Require uploads strictly inside the window                        (c1, main — origin)
|/
* 9e5bf5e  Add the upload window check                                         (c0)
```

`r1`'s body carries the trailer:

```text
(cherry picked from commit 336ad4b5103b35100d053ad2ad0801740d976a7c)
```

Content, measured (`tests/test_twins_and_transitions.py` compiles every snapshot and checks that
`accepts(20, 10, 20)` is accepted at `c0` and `rel1`, rejected at `c1` and `r1`, accepted at `r2` —
the fault arrives with the source): `main` has `return sizeKb > lower && sizeKb < upper;`;
`release` after `r1` has `return sizeKb > floor && sizeKb < ceiling;` — the
same exclusive comparison under the renamed parameters. The texts differ, so
patch-id matching between `r1` and `c1` fails; the trailer is the link that
survives.

## Expected BIC / BFC

- BIC: `r1` (`exact_set`, `required: [r1]`) — the commit in the release branch's
  history that carries the fault (direct/origin contract D4)
- `related_origins`: `c1` — the cherry-pick source; a false positive under the
  default variant, half credit under `origin-aware`
- BFC: `r2`

## Measured blame outcome at BFC^

Blaming the line `r2` deletes returns `r1`; the verifier reports `GI703`.

## What a tool must do

Report `r1`. Following the trailer to `c1` is reasonable context here and is
credited under `origin-aware`, but `c1` is not an ancestor of the fix and does
not replace `r1`. The twin SZZG-0124 has the identical trailer and there `c1`
is simply wrong.

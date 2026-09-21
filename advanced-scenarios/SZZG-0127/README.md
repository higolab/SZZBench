# SZZG-0127: Reverting a merge commit brings the merged branch's fix back out

## Purpose

A fault on `main` is fixed on a feature branch and the branch is merged. The
merge is later reverted with `git revert -m 1`, which undoes everything the
branch brought in — the fix included — so the fault is back without any commit
mentioning it. A second fix on `main` repairs it again.

## Commit structure (generated)

```text
* def2b8b  Grant the discount at the threshold again                    <- BFC (c5)
* 45f97f7  Revert "Merge branch 'feature' into main"                    <- reintroducing BIC (c4) = git revert -m 1 c3
*   cb4aad2  Merge branch 'feature' into main                           (c3)
|\
| * 4639f7a  Grant the discount at the threshold as the pricing page …  (f1, the first fix)
* | cee73c1  Describe the discount gate for the pricing team            (m1)
|/
* 896c849  Require more items than the threshold for the discount       (c1, origin)
* f3ccb97  Add the discount gate                                        (c0)
```

`c4`'s body is git's:

```text
This reverts commit cb4aad299628c135b0b53e9ab62ad7bc26ac66fd.   (= c3, the merge)
```

## Expected BIC / BFC

- BIC: `c4`, role `reintroducing` (`exact_set`, `required: [c4]`) — contract D7
- `related_origins`: `c1` — wrote the same text first; half credit under `origin-aware`
- `related_but_not_correct`: `f1` (the fix the revert undid), `c3` (the merge it undid)
- BFC: `c5`

## Measured blame outcome at BFC^

Blaming the line `c5` deletes returns `c4` (`45f97f7`): the revert rewrote the
line. The verifier reports `GI703`.

## What a tool must do

Report `c4`. Its footer names the merge `c3`, not `c1`; following footers
leads to the merge, and from there a tool needs the merge's second parent to
see that `f1` is what was undone. Reporting `c1` alone misses that the fault had
been fixed and returned.

## Factors

- `revert`
- `merge-revert`
- `reintroduction`
- `fix-on-feature-branch`

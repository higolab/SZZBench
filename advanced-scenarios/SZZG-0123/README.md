# SZZG-0123: The fix lands on the un-rebased branch, which is merged after its commits were rebased

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `rebase`, `merge`, `fix-on-feature-branch`, `origin-and-replay-both-reachable` |
| oracle | `exact_set`; required `f1`; related but not correct `r1`, `c3` · BFC `f2` |
| graph features | 2 branches; merge commit `c3`; rebase `r1` |
<!-- /szzbench:header -->

## Purpose

The rebase scenarios of the suite fix the bug on the rebased line. Here the
fault is rebased onto main, but the fix is committed on the original,
un-rebased branch, and that branch is merged afterwards. After the merge both
the original fault `f1` and its replay `r1` are ancestors of `main`, and the
fix arrived through the merge, not through the rebased line.

## Commit structure (generated)

```text
*   f38f65c  Merge branch 'feature' into main                       (c3, resolution = f2's file)
|\
| * 0362c61  Stop the attempt that exceeds the budget, and reject …  <- BFC (f2, on feature)
| * d96c2f1  Let the last permitted attempt through                  <- BIC (f1, on feature)
* | 418d0cf  Let the last permitted attempt through                  (r1, rebase_of f1)
* | d06ee66  Document the retry budget                               (m1)
|/
* 406fb6d  Add the retry budget                                      (c0)
```

The merge is a real conflict: against their common base `c0`, `r1` (ours)
changed the comparison to `<=` and `f2` (theirs) to `limit > 0 && attempts <
limit`. `resolution` supplies `f2`'s version of the file.

## Expected BIC / BFC

- BIC: `f1` (`exact_set`, `required: [f1]`) — the direct BIC in the fix's own history
- `related_but_not_correct`: `r1` (same text, not an ancestor of the fix), `c3`
  (the merge that carried the fix)
- BFC: `f2`

## Measured blame outcome

At `f2^`, blaming the line the fix deletes returns `f1` (`d96c2f1`). Along
`main` after the merge, `git log --first-parent` shows `c3, r1, m1, c0` and
never `f1` or `f2`: a first-parent tool attributes the fault to `r1` and the
fix to `c3`.

## What a tool must do

Evaluate the fix in its own history and report `f1`. Reporting `r1` because it
is the copy on `main`, or `c3` because the fix became visible there, are the
two ways to be wrong.

# SZZG-0048: Cherry-pick BIC

## Purpose

A feature branch tightens the accepted upload batch limits and is merged into
`main`. The same commit is cherry-picked onto the `release` branch, where the
bug is reported and fixed. The bug-fixing commit therefore sits on `release`,
whose history contains the **cherry-pick** but not the feature commit: the
cherry-pick is the direct BIC, and the commit it was picked from is the origin
and not an ancestor of the fix.

Before this repair the fix was on `main`, so the cherry-pick was outside the
ancestry of the bug-fixing commit and the oracle never involved it — the
scenario tested nothing about cherry-picks (GitHub issue 4).

## Commit graph (as generated)

`git log --all --graph`, with the logical ids in place of the hashes:

```text
* c4 (HEAD -> release) Accept the quota limit values again so a full batch of 50 files is allowed
* r1 Require batch sizes strictly inside the quota limits
| * c3 (main) Merge branch 'feature' into main
|/|
| * c2 (feature) Document the upload batch limits for the client team
| * c1 Require batch sizes strictly inside the quota limits
|/
* c0 Add UploadQuota with the accepted batch size limits
```

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add UploadQuota with the accepted batch size limits |
| `c1` | `feature` | c0 | `origin_bug_introducing` | Require batch sizes strictly inside the quota limits |
| `c2` | `feature` | c1 | `intermediate` | Document the upload batch limits for the client team |
| `c3` | `main` | c0, c2 | `merge` | Merge branch 'feature' into main |
| `r1` | `release` | c0 | `cherry_pick` | Require batch sizes strictly inside the quota limits *(subject and author date inherited from `c1`)* |
| `c4` | `release` | r1 | `bug_fixing` | Accept the quota limit values again so a full batch of 50 files is allowed |

Refs after generation (`git for-each-ref`): `refs/heads/main` → `c3`,
`refs/heads/feature` → `c2`, `refs/heads/release` → `c4`. Measured ancestry:
`c1` is **not** an ancestor of `c4` (`git merge-base --is-ancestor` fails),
`r1` is. `c1` is an ancestor of `main`, so the fault also lives on `main`
through the merge `c3` and stays unfixed there.

`r1`'s body carries the `-x` trailer
`(cherry picked from commit 3fe386b4f2a7f55544c2b0780837addffaa83a00)`
(measured with `git log -1 --pretty=%b`; the hash is `c1`), it keeps `c1`'s
subject (`inherit_message`) and author date `2024-01-02T10:00:00Z`
(`inherit_author_date`) while its committer date is `2024-01-05T10:00:00Z`.

## Expected SZZ result

```text
Expected BFC: c4
Required BIC: r1              (direct: the cherry-pick on the release branch)
Related but not correct: c1   (origin on the feature branch)
```

The oracle changed with this repair: `required` was `[c1]` and there was no
related list, because the fix used to be on `main`. Moving the fix to `release`
makes `r1` the direct BIC, so `required` is now `[r1]` and `c1` is the origin.
It is placed in `related_but_not_correct`, the list this suite uses for
pre-replay origins (SZZG-0047, SZZG-0072, the G5 family); the sweep of GitHub
issue 3 may move all of them to `related_origins` at once.

## Plain blame outcome (measured)

`git diff -U0 c4^ c4` deletes exactly one line,
`    return files > MIN_FILES_PER_BATCH && files < MAX_FILES_PER_BATCH;`
(line 8 of `src/main/java/example/UploadQuota.java`). `git blame` at `c4^` on
that line returns **`r1`**, the required BIC — the outcome is **hit**; `-M`,
`-C -C` and `-w` return `r1` as well. Generation reports `GI703`.

## What a tool must do to pass

Report exactly `{r1}`. Plain blame reaches `r1`, so the blame step is a control
test; the scenario discriminates on what a tool does *after* the blame:

* following the `(cherry picked from commit …)` trailer, the equal patch-id or
  the identical subject to `c1` and reporting `c1` (alone or in addition) is a
  false positive under `exact_set` — `c1` is `related_but_not_correct`;
* a tool that mines "the" branch of a repository must not answer with the
  unfixed `main` instance: the evaluated fix is on `release`, and only `release`
  contains the direct BIC.

## Behaviour check (measured)

All six commit snapshots compile with `javac` (JDK 25): 0 failures out of 6.

`acceptsBatch(int)` was probed over
`{Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 2, 49, 50, 51, MAX_VALUE-1,
MAX_VALUE}` (11 inputs: both `int` limits and both boundary constants, ±1).

* `r1` (BIC) differs from `c0` on **2 of 11** probes: `acceptsBatch(1)` and
  `acceptsBatch(50)`, the two configured limits.
* `r1` agrees with `c1` on all 11 probes — the cherry-pick reproduces the
  feature-branch behaviour exactly.
* `c4` (BFC) agrees with `c0` on **all 11** probes.

## Factors

`branch`, `cherry_pick`, `release_branch`, `direct_bic`, `origin_bic`.
Changed: `cherry_pick_of` (a schema key, `GW400`) replaced by `cherry_pick`;
`release_branch`, `direct_bic` and `origin_bic` added.

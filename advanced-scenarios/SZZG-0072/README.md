# SZZG-0072: Interactive rebase drops original BIC but bug remains

## Purpose

A feature branch tightens two independent windows of `RetryPolicy`: `f1` makes
the *delay* window exclusive, `f2` makes the *backoff* window exclusive. The
interactive rebase onto `main` **drops `f1`** and replays only `f2`. The fault
of the dropped commit therefore disappears from the rewritten history, while
the bug survives in the second window, introduced on `main` by the replayed
commit. After the rebase the feature branch is deleted, so the dropped commit
and the replay source are no longer reachable from any ref — exactly what is
left after `git rebase -i` plus a force-push that removes the branch.

## Commit graph (as generated)

```text
main      c0 ── r2 ── c3            (HEAD -> main)
            \    (replay of f2)
feature      f1 ── f2               (branch deleted by graph.ref_lifecycle)
                                    f1, f2 exist as objects but are unreachable
```

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add RetryPolicy with the accepted delay and backoff windows |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Require retry delays strictly inside the delay window |
| `f2` | `feature` | f1 | `origin_bug_introducing` | Require backoff values strictly inside the backoff window |
| `r2` | `main` | c0 | `bug_introducing` | Require backoff values strictly inside the backoff window *(subject and author date inherited from `f2`)* |
| `c3` | `main` | r2 | `bug_fixing` | Accept the backoff window bounds again so 250 ms and 60 s stay valid |

Refs after generation (measured, `git for-each-ref`): **`refs/heads/main` only**
(→ `c3`). `git log --all` and `git rev-list --all` list exactly three commits
(`c0`, `r2`, `c3`); `f1` and `f2` keep valid hashes in `commit-map.json` but are
unreachable, and `graph-map.json` records
`ref_lifecycle.deleted_branches: [feature]`.

### The replay is honest (measured)

`git show --format= --no-renames -U0` of `f2` and of `r2` produce the *same*
patch — same file, same hunk header `@@ -14 +14 @@`, same removed and added
line (only the blob index line differs, because the surrounding file differs).
`r2` changes nothing else: the delay window of `c0` is untouched, because the
commit that changed it was dropped. `r2` inherits `f2`'s subject
(`inherit_message`) and author date `2024-01-03T10:00:00Z`
(`inherit_author_date`) while its committer date is `2024-01-04T10:00:00Z`, the
author-date-before-committer-date signature of a real rebase.

## Expected SZZ result

```text
Expected BFC: c3
Required BIC: r2              (direct: the replayed commit on main)
Related but not correct: f1   (dropped original, unreachable)
                         f2   (replay source, unreachable)
```

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`    return backoffMs > MIN_BACKOFF_MS && backoffMs < MAX_BACKOFF_MS;` (line 14
of `src/main/java/example/RetryPolicy.java`). `git blame` at `c3^` on that line
returns **`r2`**, the required BIC — the outcome is **hit**; `-M`, `-C -C` and
`-w` return `r2` as well. Generation reports `GI703`.

## What a tool must do to pass

Report exactly `{r2}`. Two ways to fail:

* reporting `f1` or `f2` — a tool that is given the pre-rebase objects (a
  reflog, a fork, an `ORIG_HEAD`, or a patch-id index) may map the replayed
  commit back to its source; both are `related_but_not_correct`, i.e. false
  positives under `exact_set`;
* reporting `f1` as *the* answer because it is "the commit that introduced the
  bug" on the branch. The fault that `f1` wrote (the delay window) does not
  exist in the rewritten history at all: at `c3^` `acceptsDelay` still accepts
  its bounds. Only the backoff window survives, and it entered `main` with
  `r2`.

## Difference from SZZG-0047 (issue #11)

The two scenarios are no longer DAG/tree-equivalent with different messages
only:

| | SZZG-0047 | SZZG-0072 |
|---|---|---|
| code | `Range` (interval check + calibration window) | `RetryPolicy` (delay + backoff window) |
| branch patch(es) reaching main | both, squashed into one commit | one; the other is dropped |
| refs after generation | `main`, `feature` | `main` only |
| pre-branch commits | reachable | unreachable |
| main-line BIC diff | 3 hunks (2 constants, comparison, new method) | 1 hunk (one comparison) |

The concatenated patch sequence of the two repositories (the check used in
issue #11: `git show --format= --no-renames -U0` of every commit in
`git rev-list --all` order) differs, and so do the trees and the refs.

## Behaviour check (measured)

All five commit snapshots compile with `javac` (JDK 25), including the two
unreachable ones: 0 failures out of 5.

`acceptsDelay(int)` and `acceptsBackoff(int)` were probed over
`{Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 99, 100, 101, 249, 250, 251, 29999,
30000, 30001, 59999, 60000, 60001, MAX_VALUE-1, MAX_VALUE}` (19 inputs: both
`int` limits and every boundary constant of the source, ±1), i.e. 38 probes per
snapshot.

* `r2` (BIC) differs from `c0` on **2 of 38** probes: `acceptsBackoff(250)` and
  `acceptsBackoff(60000)` — the surviving fault.
* `r2` differs from `f2` on exactly the two *delay* probes `acceptsDelay(100)`
  and `acceptsDelay(30000)`, which is the behavioural footprint of the dropped
  commit `f1`.
* `c3` (BFC) agrees with `c0` on **all 38** probes.

## Factors

`branch`, `rebase`, `interactive_rebase`, `dropped_origin_bic`,
`deleted_branch`, `direct_bic`, `origin_bic`.
Changed: `drop` (a schema keyword, `GW400`) removed; `deleted_branch` and
`origin_bic` added.

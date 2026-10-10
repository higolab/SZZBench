# SZZG-0072: Interactive rebase drops original BIC but bug remains

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `interactive-rebase`, `dropped-commit`, `origin-vs-direct`, `deleted-branch` |
| oracle | default: `exact_set`; required `r2`; related origins `f2`, `f1` · `origin-aware`: `relaxed_with_related`; required `r2`; acceptable `f2` (credit 0.5), `f1` (credit 0.5) · BFC `c3` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r2`; ref lifecycle; 3 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

A feature branch first tightens the accepted backoff window of `RetryPolicy`
(`f1`, the commit that invents the exclusive comparison) and then reuses that
window in a new `RetryScheduler` (`f2`, which copies the comparison into the
new class). The interactive rebase onto `main` **drops `f1`** and replays only
`f2`. `RetryPolicy` is therefore inclusive again in the rewritten history — the
edit `f1` made is gone — but the scheduler still carries the exclusive
comparison that `f1` invented, so the bug survives the loss of the commit that
introduced it. After the rebase the feature branch is deleted, so the dropped
commit and the replay source are no longer reachable from any ref — exactly
what is left after `git rebase -i` plus a force-push that removes the branch.

This is what makes `f1` a genuine `origin` of `B001` and the factors
`dropped-commit` and `origin-vs-direct` real: the dropped commit is an
ancestor *of the fault*, not of an unrelated second fault. (Before this
repair `f1` tightened the *delay* window while the surviving bug was in the
*backoff* window, so `f1` had no causal link to `B001` at all — PR #33 review
finding 2.)

## Commit graph (as generated)

`git log --all --graph`, with the logical ids in place of the hashes — the
whole repository, because `f1` and `f2` are no longer reachable:

```text
* c3 (HEAD -> main) Accept the backoff window bounds in the scheduler so 250 ms and 60 s stay schedulable
* r2 Reuse the accepted backoff window in the retry scheduler
* c0 Add RetryPolicy with the accepted delay and backoff windows
```

Before the branch was deleted the history was

```text
main      c0 ── r2 ── c3        r2 = replay of f2
            \
feature      f1 ── f2           f1 dropped, f2 replayed; both unreachable now
```

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add RetryPolicy with the accepted delay and backoff windows |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Require backoff values strictly inside the backoff window |
| `f2` | `feature` | f1 | `origin_bug_introducing` | Reuse the accepted backoff window in the retry scheduler |
| `r2` | `main` | c0 | `bug_introducing` | Reuse the accepted backoff window in the retry scheduler *(subject and author date inherited from `f2`)* |
| `c3` | `main` | r2 | `bug_fixing` | Accept the backoff window bounds in the scheduler so 250 ms and 60 s stay schedulable |

Refs after generation (measured, `git for-each-ref`): **`refs/heads/main` only**
(→ `c3`). `git log --all` and `git rev-list --all` list exactly three commits
(`c0`, `r2`, `c3`); `f1` and `f2` keep valid hashes in `commit-map.json` but are
unreachable, and `graph-map.json` records
`ref_lifecycle.deleted_branches: [feature]`.

### The replay is honest (measured)

`git show --format= --no-renames -U0` of `f2` and of `r2` produce **byte-identical**
patches — the same new file `src/main/java/example/RetryScheduler.java`, the
same hunk `@@ -0,0 +1,10 @@`, the same blob index `d63a798`, because the file
`f2` adds does not depend on the rest of the tree. `r2` changes nothing else:
the backoff window of `RetryPolicy` keeps the inclusive bounds of `c0`, because
the commit that made it exclusive was dropped. `r2` inherits `f2`'s subject
(`inherit_message`) and author date (`inherit_author_date`) while its committer
date is the rebase date, the author-date-before-committer-date signature of a
real rebase.

## Expected SZZ result

```text
Expected BFC: c3
Required BIC: r2              (direct: the replayed commit on main)
Related but not correct: f1   (dropped original, unreachable, origin of the surviving fault)
                         f2   (replay source, unreachable)
```

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`    return backoffMs > RetryPolicy.MIN_BACKOFF_MS && backoffMs < RetryPolicy.MAX_BACKOFF_MS;`
(line 8 of `src/main/java/example/RetryScheduler.java`). `git blame` at `c3^` on
that line returns **`r2`**, the required BIC — the outcome is **hit**; `-w`,
`-w -M` and `-w -C -C` return `r2` as well. Generation reports `GI703`.

## What a tool must do to pass

Report exactly `{r2}`. Three ways to fail:

* reporting `f1` or `f2` — a tool that is given the pre-rebase objects (a
  reflog, a fork, an `ORIG_HEAD`, or a patch-id index) may map the replayed
  commit back to its source; both are `related_but_not_correct`, i.e. false
  positives under `exact_set`;
* reporting `f1` as *the* answer because it is "the commit that introduced the
  faulty comparison". It is: `f1` is recorded as an `origin` of `B001` and
  `OF002` is its fault. But the edit `f1` made is absent from the rewritten
  history — at `c3^` `acceptsBackoff(250)` is `true` again — and the comparison
  only reaches `main` through `r2`;
* reporting nothing because `RetryPolicy` looks correct at `c3^`. The fault
  lives in the copy inside `RetryScheduler`.

## Difference from SZZG-0047 (issue #11)

The two scenarios are not DAG/tree-equivalent with different messages only:

| | SZZG-0047 | SZZG-0072 |
|---|---|---|
| code | `Range` (interval check + calibration window) | `RetryPolicy` + `RetryScheduler` |
| branch patch(es) reaching main | both, squashed into one commit | one; the other is dropped |
| refs after generation | `main`, `feature` | `main` only |
| pre-branch commits | reachable | unreachable |
| main-line BIC diff | 3 hunks (2 constants, comparison, new method) | one new file |

The concatenated patch sequence of the two repositories (the check used in
issue #11: `git show --format= --no-renames -U0` of every commit in
`git rev-list --all` order) differs, and so do the trees and the refs.

## Behaviour check (measured)

All five commit snapshots compile with `javac` (JDK 25), including the two
unreachable ones: 0 failures out of 5.

`RetryPolicy.acceptsDelay(int)`, `RetryPolicy.acceptsBackoff(int)` and
`RetryScheduler.schedules(int, int)` were probed over
`{Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 99, 100, 101, 249, 250, 251, 29999,
30000, 30001, 59999, 60000, 60001, MAX_VALUE-1, MAX_VALUE}` (19 inputs: both
`int` limits and every boundary constant of the source, ±1) crossed with
attempts `{-1, 0, 1, 3}` for the scheduler — 115 probe keys per snapshot, with
`RetryScheduler` absent before `f2`/`r2`.

* `f1` differs from `c0` on exactly **2** keys, `acceptsBackoff(250)` and
  `acceptsBackoff(60000)` — the comparison it invents.
* `r2` differs from `f2` on exactly those **2** keys, and on nothing else: that
  is the behavioural footprint of the dropped commit `f1`.
* `r2` is the buggy state and it is visibly inconsistent: `acceptsBackoff(250)`
  is `true` (the policy accepts its own bound, because `f1` is gone) while
  `schedules(250, 1)` is `false` (the copy inside the scheduler still rejects
  it).
* `c3` (BFC) differs from `r2` on exactly **4** keys — `schedules(250, ·)` and
  `schedules(60000, ·)` for both positive attempt counts — and afterwards the
  scheduler agrees with the policy on every probed bound.

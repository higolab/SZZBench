# SZZG-0064: Rebase with non-BIC intermediate commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `rebased-bic`, `intermediate-commit`, `direct-bic`, `origin-bic`, `inherited-commit-metadata` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `r2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `r2` · BFC `c3` |
| graph features | 2 branches; rebase `r1`, `r2`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ distinguishes a rebased bug-introducing commit from the
commit that was replayed right after it in the same rebase.

This scenario is the **canonical faithful rebase** of category G5: the two
replayed commits keep the subject and the author date of their sources
(`inherit_message` / `inherit_author_date`), exactly as `git rebase` does, and
only their committer dates are new.

## Commit graph

```text
                  feature
                     |
c0 ──── f1 ───────── f2            f1, f2: the original series
 │
 └───── r1 ───────── r2 ───── c3   main
                                   r1 = replay of f1, r2 = replay of f2
```

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature -> f2
refs/heads/main    -> c3
```

No branch is deleted, so the pre-rebase commits `f1` and `f2` stay reachable.

## Commit table

| Commit | Branch | Parents | Role | Subject | Author date | Committer date |
|---|---|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check | 2024-01-01 | 2024-01-01 |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Compare the value strictly against both interval bounds | 2024-01-02 | 2024-01-02 |
| `f2` | `feature` | f1 | `intermediate` | Add a bulk membership check for the reporting module | 2024-01-03 | 2024-01-03 |
| `r1` | `main` | c0 | `bug_introducing` | *(inherited from f1)* Compare the value strictly against both interval bounds | 2024-01-02 (inherited) | 2024-01-05 09:30:00 |
| `r2` | `main` | r1 | `intermediate` | *(inherited from f2)* Add a bulk membership check for the reporting module | 2024-01-03 (inherited) | 2024-01-05 09:30:12 |
| `c3` | `main` | r2 | `bug_fixing` | Restore the inclusive comparison in Range.contains | 2024-01-08 | 2024-01-08 |

`r1` and `r2` declare no `message` of their own; the generator copies the
subject and the author date from `f1` / `f2` and records this in
`commit-map.json` under `inherits`.

## Fault and fix

`src/main/java/example/Range.java`

* `f1` / `r1` change `return value >= min && value <= max;` into
  `return value > min && value < max;`, so values equal to `min` or `max` are
  no longer reported as contained.
* `r2` adds `containsAny(int[], int, int)`; it calls `contains` but never
  touches the faulty line.
* `c3` restores the inclusive comparison.

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, r2
```

`r1` is the commit that installs the fault on `main`. `f1` is the pre-rebase
source of `r1`. `r2` is the replayed follow-up commit: reachable from the fix,
in the same file, with an author date *older* than its parent's committer
date — a plausible but wrong answer.

## Measured blame at `c3^`

`c3` deletes exactly one line
(`git show -U0 --format= c3 -- src/main/java/example/Range.java`):

```text
-    return value > min && value < max;
```

`git blame <c3^> -- src/main/java/example/Range.java` attributes that line to
**`r1`** (`0ac0f32…`, author date 2024-01-02), not to `r2` and not to `f1`.
`git blame -w` gives the same answer. Plain line-level blame therefore already
solves this scenario; the difficulty is not to be pulled to `r2` by the
"nearest neighbouring change in the same method" heuristic, and not to answer
with the unreachable-from-`main` source `f1`.

The generator's verifier reports `GI703` (basic blame reaches an expected
graph BIC).

## Measured behaviour

Snapshots `c0` (initial), `r1` (BIC) and `c3` (BFC) were compiled with
`javac 25` and `Range.contains(int, int, int)` was executed over the full grid
of all 9³ = 729 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

* `c0` vs `r1`: **81 of 729 inputs differ** (every input with `value == min`
  or `value == max`).
* `c0` vs `c3`: **identical on all 729 inputs**.

`containsAny(int[], int, int)` exists only from `r2` on and is not shared with
the initial snapshot; it delegates to `contains`.

All 6 commit snapshots compile with `javac` without errors.

## What a tool must do to pass

1. Return exactly `{r1}`.
2. Not return `r2`, although `r2` is the other half of the replayed series and
   touches the same file and method body.
3. Not return `f1` as the answer: `f1` is the pre-rebase origin, recorded as
   `related_but_not_correct`, and is not an ancestor of the fix.

## Difference from SZZG-0078

SZZG-0078 is the other G5 scenario about a replayed BIC. It is now a four
commit history over a different class (`Interval.overlaps`), its replayed
commit carries an explicit subject plus a machine-readable origin footer in
the commit body, and its dates lie in February 2024. This scenario has six
commits over `Range.contains`, no footer, and inherited subjects and author
dates. The two generated repositories share no patch (see the scenario review
for issue #11).

## Notes

- Rebase relationships are recorded with `rebase_of`; `inherit_message` and
  `inherit_author_date` reproduce what `git rebase` keeps from the source.
- `rebase_of` does not replay the source commit; the `operations` describe the
  rebased content.

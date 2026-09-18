# SZZG-0073: Interactive rebase reorders commits before BIC

## Purpose

Evaluate whether SZZ survives an interactive rebase that replays the commits
of a branch **in a different order** than they were written. The commit that
was written *after* the fault ends up *before* it on `main`.

## Commit graph

```text
        feature:  c0 ── f1 ───────── f2        f1 first, f2 second
                         (fault)     (clamp)

        main:     c0 ── r1 ───────── r2 ── c3  r1 = replay of f2 (clamp)
                        (clamp)      (fault)   r2 = replay of f1 (fault)
```

`git rev-list --parents`: `c3 <- r2 <- r1 <- c0` on `main` and
`f2 <- f1 <- c0` on `feature`.

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature -> f2
refs/heads/main    -> c3
```

## Which commit moved

**`f2` moved.** On `feature` the developer first made `contains` compare
strictly (`f1`) and then added the `clamp` helper (`f2`). During
`git rebase -i` the two `pick` lines were swapped, so on `main` the clamp
commit is replayed first (`r1`, `rebase_of: f2`) and the faulty comparison
second (`r2`, `rebase_of: f1`).

The reorder is visible in the generated repository without reading the
scenario metadata, because both replayed commits inherit the subject and the
author date of their source (`git log --date=iso-strict`):

```text
main:     3051f1a aD=2024-01-03  Add a clamp helper for values outside the interval   (= r1, replay of f2)
          5ef5ff2 aD=2024-01-02  Use strict comparisons for the interval bounds       (= r2, replay of f1)
feature:  e4268d2 aD=2024-01-03  Add a clamp helper for values outside the interval   (= f2)
          b6ab969 aD=2024-01-02  Use strict comparisons for the interval bounds       (= f1)
```

Along `main` the author dates **decrease** (2024-01-03 then 2024-01-02) while
the committer dates increase (11:00:00 then 11:00:07); along `feature` both
increase. The rebase is otherwise faithful: `tree(r2) == tree(f2) ==
dd9510ed…`, and the patch of `r2` is byte-identical to the patch of `f1`.

## Commit table

| Commit | Branch | Parents | Role | Subject | Author date |
|---|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check | 2024-01-01 |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Use strict comparisons for the interval bounds | 2024-01-02 |
| `f2` | `feature` | f1 | `intermediate` | Add a clamp helper for values outside the interval | 2024-01-03 |
| `r1` | `main` | c0 | `intermediate` | *(inherited from f2)* Add a clamp helper for values outside the interval | 2024-01-03 |
| `r2` | `main` | r1 | `bug_introducing` | *(inherited from f1)* Use strict comparisons for the interval bounds | 2024-01-02 |
| `c3` | `main` | r2 | `bug_fixing` | Restore the inclusive comparison in Range.contains | 2024-01-10 |

## Expected SZZ result

```text
Expected BIC(s): r2
Related but not correct: f1, r1
```

`r2` installs the fault on `main` although it replays the *first* commit of
the feature branch. `r1` replays the *later* feature commit and only adds
`clamp`. `f1` is the pre-rebase source of `r2`.

## Measured blame at `c3^`

`c3` deletes exactly one line:

```text
-    return value > min && value < max;
```

`git blame <c3^> -- src/main/java/example/Range.java` attributes that line to
**`r2`** (`5ef5ff2…`), the lines of `clamp` to `r1` (`3051f1a…`) and the rest
to `c0`. `git blame -w` gives the same answer. The generator's verifier
reports `GI703`.

## Measured behaviour

Snapshots `c0` (initial), `r2` (BIC) and `c3` (BFC) were compiled with
`javac 25`; every public `int`-only method was executed over the full grid of
all 9³ = 729 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

| method | shared by | `c0` vs `r2` | `c0` vs `c3` |
|---|---|---|---|
| `contains(int,int,int)` | c0, r2, c3 | **81 of 729 inputs differ** | **0 differ** |
| `clamp(int,int,int)` | r2, c3 only (added by `r1`) | – | `r2` vs `c3`: 0 of 729 differ |

All 6 commit snapshots compile with `javac` without errors.

## What a tool must do to pass

1. Return exactly `{r2}`.
2. Not return `r1`, although `r1` is the *first* commit of the replayed series
   and its author date is the *newest* of the two.
3. Not assume that the n-th replayed commit corresponds to the n-th source
   commit: here `rebase_of` maps `r1 -> f2` and `r2 -> f1`.

## Notes

- `interactive_rebase: reorder` records the rewrite action; `rebase_of` records
  the source of each replayed commit.
- `rebase_of` does not replay the source commit; the `operations` describe the
  rebased content, which is why `r1` applies the clamp patch to the pristine
  file and `r2` applies the comparison patch on top of it.

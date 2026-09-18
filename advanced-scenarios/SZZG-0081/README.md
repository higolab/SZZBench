# SZZG-0081: Rebase with formatting rewrite noise

## Purpose

Evaluate robustness against a **whitespace-only reformatting commit that
rewrites the faulty line itself** between the rebased bug-introducing commit
and the fix. Plain line-level blame stops at the reformatting commit;
`git blame -w` reaches the bug-introducing commit.

## Commit graph

```text
        feature
          |
c0 ────── f1                        f1: the original change
 │
 └─────── r1 ── r2 ── c3   main     r1 = replay of f1
                                    r2 = project formatter (whitespace only)
                                    c3 = the fix
```

`git rev-list --parents`: `c3 <- r2 <- r1 <- c0` on `main`; `f1 <- c0` on
`feature`.

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature -> f1 (9a41742)
refs/heads/main    -> c3 (980bf9b)
```

## Commit table

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Use strict comparisons for the interval bounds |
| `r1` | `main` | c0 | `bug_introducing` | *(inherited from f1)* Use strict comparisons for the interval bounds |
| `r2` | `main` | r1 | `formatting` | Apply the four-space indentation of the project formatter |
| `c3` | `main` | r2 | `bug_fixing` | Restore the inclusive comparison in Range.contains |

## The formatting commit really rewrites the faulty line

`r2` re-indents **every** indented line of `src/main/java/example/Range.java`
from two-space to four-space indentation. The faulty line changes from

```text
    return value > min && value < max;
```

to

```text
        return value > min && value < max;
```

Measured in the generated repository:

* `git show --stat r2`: `1 file changed, 6 insertions(+), 6 deletions(-)` —
  six rewritten lines, among them the faulty one.
* `git diff -w r1 r2` is **empty**: the commit is whitespace-only and token
  identical, so it is behaviour preserving by construction.

(The previous version of this scenario only inserted a comment line above the
method and never touched the faulty line, and the `history_summary` wrongly
called it a "line ending rewrite".)

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, r2
```

## Measured blame at `c3^` — both variants

`c3` deletes exactly one line:

```text
-        return value > min && value < max;
```

| command | commit reached | logical id |
|---|---|---|
| `git blame <c3^> -- src/main/java/example/Range.java` | `5f3c57ce…` | **`r2`** (the formatting commit) |
| `git blame -w <c3^> -- src/main/java/example/Range.java` | `7a9195c6…` | **`r1`** (the bug-introducing commit) |

This blame miss is the point of the scenario, so the graph verifier reports

```text
[WARNING] GW703: bug B001: basic git blame reaches 5f3c57ce…, not expected graph BIC hash(es).
```

That warning is **expected and not silenced**; generation itself reports 0
errors.

## Measured behaviour

Snapshots `c0` (initial), `r1` (BIC), `r2` (formatting) and `c3` (BFC) were
compiled with `javac 25`; every public `int`-only method was executed over the
full grid of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`
(9³ = 729 inputs for `contains`, 9² = 81 for `containsZero`):

| method | `c0` vs `r1` | `c0` vs `r2` | `c0` vs `c3` |
|---|---|---|---|
| `contains(int,int,int)` | **81 of 729 differ** | 81 of 729 differ | **0 differ** |
| `containsZero(int,int)` | **9 of 81 differ** | 9 of 81 differ | **0 differ** |

`r2` behaves exactly like `r1`, which confirms that the reformatting changed
nothing but whitespace. All 5 commit snapshots compile with `javac` without
errors.

## What a tool must do to pass

1. Return exactly `{r1}`.
2. Not return `r2`, although plain `git blame` at the fix points straight at
   it. A tool needs whitespace-insensitive blame (`git blame -w`),
   `--ignore-rev`/`.git-blame-ignore-revs`, or an equivalent "skip
   behaviour-preserving commits" heuristic.
3. Not return `f1` as the answer: it is the pre-rebase origin and is not an
   ancestor of the fix.

## Notes

- `rebase_cleanup: formatting_rewrite` records that the reformatting was part
  of the rebase cleanup.
- `r1` uses `inherit_message` / `inherit_author_date`, so it keeps `f1`'s
  subject and author date (2024-01-02) with a new committer date (2024-01-04).

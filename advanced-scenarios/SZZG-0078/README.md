# SZZG-0078: Rebase commit message reveals origin

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `commit-messages`, `message-trailer`, `origin-vs-direct` |
| oracle | default: `exact_set`; required `r1`; related origins `f1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5) · BFC `c2` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r1`; cherry-pick `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`); `developer_hints` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether an origin reference *inside the commit message* helps or
misleads SZZ when the bug-introducing commit on `main` is a replay of a commit
that lives on another branch.

The origin reference is real Git content, not scenario metadata: the subject
of the replayed commit quotes the subject of its source verbatim, and the body
carries the `(cherry picked from commit <hash>)` footer that `git cherry-pick -x`
writes. The hash resolves to a commit that is reachable in the generated
repository.

## Commit graph

```text
        review
          |
c0 ────── f1              f1: the original change
 │
 └─────── r1 ───── c2     main
                          r1 = replay of f1, c2 = the fix
```

Refs after generation (`git for-each-ref`):

```text
refs/heads/main   -> c2
refs/heads/review -> f1
```

The `review` branch is not deleted, so the hash in the footer of `r1` resolves.

## Commit table

| Commit | Branch | Parents | Role | Subject | Author date | Committer date |
|---|---|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Interval class with an overlap check | 2024-02-05 | 2024-02-05 |
| `f1` | `review` | c0 | `origin_bug_introducing` | Treat touching intervals as disjoint | 2024-02-06 | 2024-02-06 |
| `r1` | `main` | c0 | `bug_introducing` | Carry over "Treat touching intervals as disjoint" from the review branch | 2024-02-06 | 2024-02-09 16:40 |
| `c2` | `main` | r1 | `bug_fixing` | Restore the inclusive endpoint comparison in Interval.overlaps | 2024-02-14 | 2024-02-14 |

`git log -1 --format=%B r1` in the generated repository:

```text
Carry over "Treat touching intervals as disjoint" from the review branch

(cherry picked from commit b0dd055b65526241c250601b889105ba636b3f73)
```

`b0dd055…` is the hash of `f1` (the hashes are reproducible: every commit has
explicit or deterministic author/committer metadata).

## Fault and fix

`src/main/java/example/Interval.java`

* `f1` / `r1` change
  `return firstStart <= secondEnd && secondStart <= firstEnd;` into
  `return firstStart < secondEnd && secondStart < firstEnd;`, so two intervals
  that share an endpoint are no longer reported as overlapping.
* `c2` restores the inclusive comparison.

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

The message names `f1`, but `f1` is not an ancestor of the fix: the direct BIC
stays `r1`. A message-aware tool may use the footer to *explain* `r1`, or to
report `f1` as origin-related, but must not answer with `f1` instead of `r1`.

## Measured blame at `c2^`

`c2` deletes exactly one line:

```text
-    return firstStart < secondEnd && secondStart < firstEnd;
```

`git blame <c2^> -- src/main/java/example/Interval.java` attributes that line
to **`r1`** (`886d55f…`); `git blame -w` gives the same answer. The generator's
verifier reports `GI703`.

Line-level blame alone therefore already answers this scenario; the message
footer is the *additional* evidence whose use is being evaluated — and the
scenario checks that a tool does not let it override the blame result.

## Measured behaviour

Snapshots `c0` (initial), `r1` (BIC) and `c2` (BFC) were compiled with
`javac 25` and `Interval.overlaps(int, int, int, int)` was executed over the
full grid of all 9⁴ = 6561 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

* `c0` vs `r1`: **729 of 6561 inputs differ**.
* `c0` vs `c2`: **identical on all 6561 inputs**.

All 4 commit snapshots compile with `javac` without errors.

## What a tool must do to pass

1. Return exactly `{r1}`.
2. Not replace `r1` with `f1` because the message of `r1` points at `f1`.
3. If the tool reads messages: resolve the footer hash to `f1` and report it as
   origin-related context (`related_but_not_correct` in this scenario's
   oracle), not as the answer.

## Difference from SZZG-0064

SZZG-0064 is the faithful rebase of a two commit series over
`Range.contains(int,int,int)`: six commits, inherited subjects and author dates,
no footer, January 2024 dates. This scenario is a four commit history over
`Interval.overlaps(int,int,int,int)` with an explicit subject and a
machine-readable origin footer, February 2024 dates. Concatenating
`git show --format= --no-renames -U0` over `rev-list --all --topo-order` gives
`c6f085ad…` (2108 bytes) for SZZG-0064 and `ddedfb57…` (1500 bytes) for
SZZG-0078. No patch and no source line is shared; the only lines the two
sequences have in common are generic (`package example;`, `}`, `  }` and diff
headers). Issue #11 flagged the previous versions as patch-identical.

## Notes

- `r1` declares both `rebase_of` (the rewrite relation) and `cherry_pick_of`
  (the source of the footer written by `cherry_pick_trailer`). Because `r1`
  carries `operations`, the generator does not run `git cherry-pick`; the
  operations describe the replayed content, as for every `rebase_of` commit.
- The scenario's `developer_hints` entry now describes the footer that really
  exists in the repository instead of the YAML-only `Rebased-from: f1` hint.

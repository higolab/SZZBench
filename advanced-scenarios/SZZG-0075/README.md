# SZZG-0075: Interactive rebase squashes BIC and BFC into neutral commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `interactive-rebase`, `squash`, `transient-bug`, `scope-boundary`, `no-main-line-bfc` |
| oracle | default: `exact_set`; required `f1`; related but not correct `r1` · `main-line-only`: `exact_set`; expects no BIC · BFC `f2` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches; rebase `r1`; ref lifecycle; operation `apply_squash`; 1 evaluation variant (`main-line-only`) |
<!-- /szzbench:header -->

## Purpose

Make the **squashed main-line commit** the object of the scenario: a fault and
its fix are written on a feature branch and squashed into one commit before the
branch reaches `main`. The two cancel out, so the main line contains neither
the faulty statement nor a separate fix, and there is no main-line bug-fixing
commit that SZZ could start from. The pre-squash pair stays reachable on the
feature branch.

## Commit graph

```text
        feature:  c0 ── f1 ───── f2        f1: width helper, one too small
                        (fault)  (fix)     f2: fix

        main:     c0 ── r1                 r1 = squash(f1, f2): the helper in
                                            its correct form
```

`git rev-list --parents`: `r1 <- c0` on `main`; `f2 <- f1 <- c0` on `feature`.
`r1` is an ordinary single-parent commit — a squash is not a merge.

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature          -> f2 (d255b24)
refs/heads/main             -> r1 (41729b3)
refs/tags/pre-squash/feature -> f2 (d255b24)
```

**The pre-squash commits stay reachable**: the `feature` branch is not deleted
and `graph.ref_lifecycle` additionally tags `f2` as `pre-squash/feature`, so
`f1` and `f2` are reachable from two refs and are never garbage collected.

## Commit table

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check |
| `f1` | `feature` | c0 | `bug_introducing` | Add a width helper for an interval |
| `f2` | `feature` | f1 | `bug_fixing` | An inclusive interval is one element wider than max - min |
| `r1` | `main` | c0 | `intermediate` | Add a width helper that counts both endpoints |

## The two changes really cancel out

`f1` adds `public int width(int min, int max)` returning `max - min`, which is
one too small for an inclusive interval; `f2` changes it to `max - min + 1`.
`r1` is generated with `apply_squash` (`git cherry-pick --no-commit f1`, then
`f2`), so its tree is the result of applying both patches.

Measured in the generated repository:

* `tree(r1) == tree(f2) == 663fa41c…`
* `git show --stat r1`: `1 file changed, 4 insertions(+)` — a pure addition;
  there is no fix hunk, because there is nothing to fix.
* The faulty statement `return max - min;` occurs **once in the tree of `f1`
  and in no other tree**, in particular in no tree reachable from `main`.
* `git log -S 'return max - min;' main` prints **nothing**: no commit on the
  main line ever added or removed the faulty statement.

## Expected SZZ result

```text
Default oracle       : given the feature-branch fix f2, expected BIC(s) = f1
                       related but not correct: r1
Variant main-line-only: expect_no_bic — the expected answer is the empty set
```

**What a tool is expected to return for a main-line BFC.** There is no
main-line BFC for B001. A tool that mines `main` for bug-fixing commits finds
none for this bug, so the correct output is *nothing*. The scenario declares
this explicitly as the evaluation variant `main-line-only` with
`expect_no_bic: true` and an empty `required` set; under that variant every
commit a tool reports is a false positive — in particular `r1`, which is the
only commit on `main` that touches the method and whose message and squash
metadata make it look like the place where the feature (and therefore the
fault) entered. `r1` is listed as `related_but_not_correct` in the default
oracle for the same reason.

Scoring the bug at all therefore requires the pre-squash pair on `feature`,
which is why the default oracle uses `f2` as the BFC and expects `f1`.

## Measured blame at `f2^`

`f2` deletes exactly one line:

```text
-    return max - min;
```

`git blame <f2^> -- src/main/java/example/Range.java` attributes that line to
**`f1`** (`480246f…`); `git blame -w` gives the same answer. The generator's
verifier reports `GI703`. Note that this blame runs entirely inside the
feature branch — on `main` there is no line to blame.

## Measured behaviour — the contract of the squash

Snapshots `c0`, `f1`, `f2` and `r1` were compiled with `javac 25`; every public
`int`-only method was executed over the full grid of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`
(9³ = 729 inputs for `contains`, 9² = 81 for `width`):

| claim | measurement |
|---|---|
| the squash equals the fixed feature tip | `width`: `f2` vs `r1` **0 of 81 inputs differ** |
| the squash is not the faulty version | `width`: `f2` vs `f1` **81 of 81 inputs differ** |
| the squash changes nothing else | `contains`: identical across `c0`, `f1`, `f2`, `r1` (729 inputs) |
| the main line never had the fault | `width` does not exist at `c0`; the only other main-line commit is `r1` |

All 4 commit snapshots compile with `javac` without errors.

## What a tool must do to pass

1. Under the default oracle (BFC `f2`): return exactly `{f1}`.
2. Under `main-line-only`: return nothing. Reporting `r1` — the squashed
   commit, the only main-line commit that adds `width` — is a false positive.
3. Not treat `r1` as a bug-introducing commit for a bug whose faulty statement
   its tree does not contain.

## Notes

- `squashes` and `interactive_rebase: squash` record the rewrite; `rebase_of:
  [f1, f2]` records both sources.
- The squash is really generated by applying both patches (`apply_squash`), not
  by writing the end state by hand.

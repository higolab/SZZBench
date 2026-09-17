# SZZG-0047: Squash merge

## Purpose

A feature branch makes the interval check of `Range` exclusive and then adds a
calibration window that reuses it. The branch reaches `main` as a **single
GitHub squash commit**, so the faulty comparison enters the main-line history
in a commit that has one parent and is not a merge. The direct BIC on `main` is
that squash commit; the feature-branch commit that first wrote the comparison
is the origin and is not an ancestor of the bug-fixing commit.

## Commit graph (as generated)

```text
main      c0 ──────────────── c3 ── c4        (HEAD -> main)
            \                 (squash, 1 parent)
feature      c1 ── c2                          (feature)
```

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add Range with the supported sample window |
| `c1` | `feature` | c0 | `origin_bug_introducing` | Require samples strictly inside the range bounds |
| `c2` | `feature` | c1 | `intermediate` | Add the calibration window check used by the sampler |
| `c3` | `main` | c0 | `bug_introducing` | Tighten the range bounds and add the calibration window check (#118) |
| `c4` | `main` | c3 | `bug_fixing` | Accept the range bounds again so min and max stay inside the range |

Refs after generation (`git for-each-ref`): `refs/heads/main` → `c4`,
`refs/heads/feature` → `c2`. Both branches are kept: a squash merge does not
rewrite the source branch, and GitHub keeps the head branch until it is
deleted. `git rev-list --parents --all` shows `c3` with exactly one parent
(`c0`), so the squash commit is not a merge commit.

`c3` is generated with `apply_squash: [c1, c2]`, i.e. both feature patches are
really applied on top of `c0`; its diff against `c0` is the combined feature
diff (three hunks: the two new constants, the changed comparison, the new
method). The `squashes:` metadata names the same two commits.

### About the squash message

The subject is the GitHub squash subject of pull request #118. GitHub also
writes the squashed subjects as a bullet list into the message *body*; the
generator writes single-line subjects only (`graph_verifier` compares `%s`
with `message`, error `GE623`), so the two squashed subjects are recorded in
`squashes:` and in the table above instead of in the commit body.

## Expected SZZ result

```text
Expected BFC: c4
Required BIC: c3          (direct: the squash commit that put the line into main)
Related but not correct: c1   (origin on the feature branch)
```

## Plain blame outcome (measured)

`git diff -U0 c4^ c4` deletes exactly one line,
`    return value > min && value < max;` (line 10 of
`src/main/java/example/Range.java`). `git blame` at `c4^` on that line returns
**`c3`**, i.e. the required BIC — the outcome is **hit**. The variants
`git blame -M`, `-C -C` and `-w` return `c3` as well. The generator's
verification therefore reports `GI703` ("basic git blame reaches an expected
graph BIC"), not `GW703`.

## What a tool must do to pass

Report exactly `{c3}`. Plain line blame already reaches `c3`, so the scenario
is a **control test** for the blame step; the difficulty is on the other side:
a tool that follows the `squashes:` metadata, the patch identity of `c1`, or a
`-C` copy search across branches may additionally report `c1`, which is a false
positive under `exact_set` (`c1` is listed as `related_but_not_correct`, i.e. a
diagnostic bucket, not a correct answer). The scenario asks whether a tool can
represent a single-parent squash commit as the direct BIC without either
falling back to the feature branch or treating `c3` as a merge.

## Behaviour check (measured)

All five commit snapshots compile with `javac` (JDK 25): 0 failures out of 5.

The public methods `contains(int,int,int)`, `isSupportedSample(int)` and (from
`c2`/`c3` on) `isWithinCalibrationWindow(int)` were probed over
`value ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -41, -40, -39, -1, 0, 1, 79, 80, 81,
124, 125, 126, MAX_VALUE-1, MAX_VALUE}` (16 inputs: both `int` limits and every
boundary constant in the source, ±1), with `(min,max) ∈ {(-40,125), (0,80),
(0,100)}` for the three-argument method — 64 probes per snapshot for the
methods `c0` already has, 80 for the later ones.

* `c3` (BIC) differs from `c0` on **7 of 64** shared probes, all of them at a
  boundary: `contains(-40,-40,125)`, `contains(125,-40,125)`, `contains(0,0,80)`,
  `contains(80,0,80)`, `contains(0,0,100)`, `isSupportedSample(-40)` and
  `isSupportedSample(125)`.
* `c3` reproduces the feature-branch tip `c2` exactly (80 of 80 probes equal),
  which is what makes it a squash of `c1` and `c2`.
* `c4` (BFC) agrees with `c0` on **all 64** shared probes; the 16 extra probes
  of `isWithinCalibrationWindow` have no counterpart at `c0` because the method
  is added by the squashed feature work.

## Factors

`branch`, `squash_merge`, `squashed_bic`, `direct_bic`, `origin_bic`
(unchanged).

# SZZG-0114: Huge history

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `generated-history` |
| oracle | `exact_set`; required `c1` · BFC `c4` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | generated commits (`commit_generator`); operation `write_generated_text_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ still finds the bug-introducing commit when **a thousand unrelated
commits** separate it from the fix, and whether the tool scales to such a history. The
defect itself is one line inside a generated 10,000-entry Java class.

Before this repair, `commit_generator` only wrote a marker file, so the repository had five
commits while `commit_generators.count: 1000` claimed a thousand, and `LargeRange.java` was
10,000 top-level fields with no class, which `javac` rejects (issues #4 and #10).

## Commit graph

```text
c0 ─► c1 ─► [c2.g1 … c2.g500] ─► c2 ─► [c3.g1 … c3.g500] ─► c3 ─► c4     (branch: main, linear)

c0  Add the generated bounds table and the tier policy      LargeRange.java (10,005 lines) + TierPolicy.java
c1  Refresh the bounds table from the tier export           <- BIC: VALUE_5000 becomes -1
c2  Open the 2024.2 release notes                           owns 500 generated catalog-sync commits
c3  Record the telemetry export in the release notes        owns 500 generated telemetry-export commits
c4  Correct the bound of tier 5000 in the generated table   <- BFC
```

The 1000 generated commits each append one line to a file under `generated/catalog` or
`generated/telemetry`; their messages are neutral
(`Update generated/catalog/catalog_sync-09.txt (catalog_sync 499/500)`).

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c4`

## Measured plain-blame outcome at BFC^

`BFC^` is `c3`, 1003 commits after the BIC. The BFC deletes exactly one line, line 5004 of a
10,005-line file:

```text
src/main/java/example/LargeRange.java:5004
  "  public static final int VALUE_5000 = -1;"  ->  c1
```

Outcome: **exact** (`GI703`). The difficulty is not ambiguity but scale: the answer is 1003
commits back, in the middle of a 437 KiB file.

## What a tool must do to pass

- Report exactly `{c1}`.
- Walk back over 1000 intervening commits without truncating the history, sampling it or
  timing out, and without reporting any of the generated commits — none of them touches
  `src/` at all.

## Structural evidence (measured on the generated repository)

```text
$ git rev-list --count HEAD            -> 1005      (5 logical + 1000 generated)
$ git rev-list --all --count           -> 1005
$ git rev-list --count c1..HEAD        -> 1003      (commits between the BIC and HEAD)
$ git log --format=%H -- src | wc -l   -> 3         (only c0, c1 and c4 touch the sources)
```

`commit-map.json` holds 1005 entries, 1000 of them with `role: generated`
(`c2.g1 … c2.g500`, `c3.g1 … c3.g500`); `c2` and `c3` each record 500 entries in
`generated_commits`, and `graph-map.json` lists `{c2: 500, c3: 500}`. Every generated commit
has `timestamp_placement: spaced`, so author and committer dates are strictly increasing
between the parent and the owner. This matches the two `commit_generator` operations
(`catalog_sync` with `count: 500` in `c2`, `telemetry_export` with `count: 500` in `c3`,
1000 in total).

`javac` (JDK 25, `-proc:none`) compiles **every one of the 1005 commit snapshots** without a
failure (measured: 1005 snapshots, 0 failures, 342 s); the sources take one of two states
across the history (`c0`/`c4` and `c1`…`c3`), because no generated commit touches `src/`.

## Behaviour check (measured)

10,015 probes per snapshot: `TierPolicy.upperBound(int)` on
`{MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 2, 500, 4999, 5000, 5001, 9999, 10000, 10001, MAX_VALUE-1, MAX_VALUE}`
(both `int` limits and the four tier constants written in `TierPolicy`), plus every one of
the 10,000 public constants of `LargeRange` read reflectively and compared with its index.

- `c0`: `upperBound(5000) = 5000`; constants sum `50005000`, 0 mismatches.
- `c1` (BIC): `upperBound(5000) = -1` — indistinguishable from the "unknown tier" answer;
  constants sum `49999999`, exactly 1 mismatch (`VALUE_5000 = -1`).
- `c4` (BFC): **identical to `c0`** on all 10,015 probes.

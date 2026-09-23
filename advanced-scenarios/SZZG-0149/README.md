# SZZG-0149: Three release branches, three causes, and a credit threshold blame cannot meet

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `branch`, `release-branch`, `merge`, `multi-bic`, `single-bfc`, `partial-credit`, `addition-only-fix`, `missing-branch`, `off-by-one`, `blame-unreachable-bic` |
| oracle | `partial_credit`; required `c1`, `c3`, `c5`; minimum 2 · BFC `c7` |
| defeats | `blame`, `shape`, `position` |
| graph features | 3 branches; merge commits `c2`, `c4`; 3 BICs; 3 fault sites; policy `partial_credit` |
<!-- /szzbench:header -->

## Purpose

G4 held 27 of its 29 scenarios in the cheaply-solved set, the second largest
pocket in the suite, and every one of them had a one-commit oracle — which a
positional rule names by construction
(`tests/test_second_mechanism.py`). This one names **three** commits under
`partial_credit` with `minimum_required: 2`, and puts them on three branches, so
a tool has to cross two merges as well as reach past what the fix deletes. It is
G4's first three-commit oracle and its first history with three branches.

It is the branched twin of [SZZG-0148](../SZZG-0148/README.md), which has the
same policy and threshold on a linear history, and of
[SZZG-0138](../SZZG-0138/README.md), the control where blame reaches two of
three and therefore passes.

## Commit graph

```text
c0 ──┬──────────────► c2 ──► c4 ──► c5 ──► c6 ──► c7      main
     │               ╱      ╱
     ├── c1 ────────╯      ╱                              release-transit
     └── c3 ──────────────╯                               release-zones

c0  Add the delivery quote                       deliveryDays = distanceKm / 500 + 1
c1  Count only the full 500 km legs of the transit   distanceKm / 500          <- BIC
c2  Merge branch 'release-transit'
c3  Add the zone surcharge table                 switch with no REMOTE case    <- BIC
c4  Merge branch 'release-zones'
c5  Quote express delivery a day sooner          expressDays with no floor     <- BIC
c6  Document what the quote and the surcharge table are for   a Javadoc line on each class
c7  Count the last leg, charge the remote zone and keep express at a day       <- BFC
```

Both merges are clean: `release-transit` edits `Quote.java` and `release-zones`
adds `Surcharge.java`.

## Expected BIC / BFC

- BICs: `c1`, `c3` and `c5` (`partial_credit`, `required: [c1, c3, c5]`,
  `minimum_required: 2`)
- BFC: `c7`

Any two of the three pass; one does not. A false positive still fails.

## Measured behaviour

`deliveryDays(1200)`, `deliveryDays(200)`, `expressDays(200)`,
`expressDays(1200)`, `Surcharge.cents("RURAL")` and `cents("REMOTE")` at each
commit (`tests/test_largest_pockets.py`; `Surcharge` exists from `c3` on its
branch and on main from `c4`, `expressDays` from `c5`):

| commit | days 1200 | days 200 | express 200 | express 1200 | rural | remote |
|---|---|---|---|---|---|---|
| `c0` | 3 | 1 | — | — | — | — |
| `c1`, `c2` | **2** | **0** | — | — | — | — |
| `c3` (branch) | 3 | 1 | — | — | 500 | **0** |
| `c4` | **2** | **0** | — | — | 500 | **0** |
| `c5`, `c6` | 2 | 0 | **-1** | 1 | 500 | **0** |
| `c7` | 3 | 1 | 1 | 2 | 500 | 1500 |

`c3` is measured on its own branch, where `c1` is not present, which is why the
transit figures there are `c0`'s. `c6` adds a Javadoc line to each class and
moves nothing. The three causes are independent: each moves answers the others
do not touch.

`c6` is also what keeps the **shape** baseline out. That rule names the newest
commit to touch each file the fix touches, and the fix touches two: without a
commit between `c5` and the fix, it would answer `{c3, c5}` — two of the three
required commits, which is exactly the threshold. With `c6` there it answers
`{c6}`, a commit that introduced nothing.

## Measured blame outcome at BFC^

The fix's diff is **one deletion and six additions**. The single deleted line is
`c1`'s:

```text
"return distanceKm / 500;"   plain -> c1   -w -> c1   -w -C -C -> c1
```

The repair of `c3`'s omission adds a `case` to the switch and the repair of
`c5`'s adds a floor above the existing return; neither deletes anything. So
blame answers `{c1}`: **one** of three required commits, with no false positive,
and `minimum_required` is 2.

## What a tool must do to pass

Report at least two of `{c1, c3, c5}` and nothing else. One is on a deleted
line. The other two have to be reached from what the fix *adds*: a `case`, back
across the `release-zones` merge to the commit that wrote the switch without it,
and a floor, back to the commit that wrote the subtraction without one. A report
should state the credit ratio and the threshold it was scored against.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. Every position rule names one commit, which is below the
threshold; `position-all-non-fix` and every author rule add a commit outside the
required set. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

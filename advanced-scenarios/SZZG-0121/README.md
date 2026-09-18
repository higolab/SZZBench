# SZZG-0121: A cherry-picked unit change in a file the fix never opens

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. It is the
third instance of the *other-file* kind — after
[SZZ-0194](../../scenarios/SZZ-0194/README.md) (a Java file) and
[SZZ-0199](../../scenarios/SZZ-0199/README.md) (a properties file) — and adds a
second question on top: the unreachable commit exists **twice**, and only the
copy in the fix's own history is the answer.

## Commit structure

```text
* 3500906  Show the surcharge rate as a percentage   ratePercent(zone)          <- BFC (c3)
* 9a109ba  Show the surcharge rate on the shipment   adds displayedRatePercent  <- BIC (c2)
* 677d5aa  Hold the surcharge rates in per mille     cherry-pick of efdfd5a     <- BIC (r1)
| * efdfd5a  Hold the surcharge rates in per mille   (c1, branch feature-rates)
|/
* 8c25f33  Add the surcharge table and the shipment  ratePercent = 12 / 3 (c0)
```

`c1` is developed on `feature-rates` and cherry-picked onto main as `r1`. The
branch is never merged, so **`c1` is not an ancestor of the fix** — measured
with `git merge-base --is-ancestor` — and `r1` carries the usual trailer:

```text
(cherry picked from commit efdfd5aa92310e69cb004a6b1e4937c2973cdc72)
```

## Expected BIC / BFC

- BICs: `r1` and `c2` (`exact_set`, `required: [r1, c2]`)
- `related_but_not_correct`: `c1` — the same change, but not in the history the fix belongs to
- BFC: `c3`

## Measured behaviour (from the generated repository)

Along main's first-parent history, how many **shared** probe keys change value
and how many appear:

```text
c0  Add the surcharge table and the shipment   175 probes
r1  Hold the surcharge rates in per mille      changed 0, added 7   <- ratePercent still answers 3
c2  Show the surcharge rate on the shipment    changed 0, added 7   <- displayedRatePercent = 30
c3  Show the surcharge rate as a percentage    changed 7            <- displayedRatePercent = 3
```

The unit change keeps `ratePercent` and `surchargeCents` answering exactly what
they answered before, so no caller in the repository can see it. `c2` is the
first commit to read the raw table value, and reports 30% where the rate is 3%.

**Both commits are necessary, measured rather than argued.** Undoing the unit
change on top of `c2` — the tree in which the faulty display exists but the
table is still in percent — makes `displayedRatePercent` agree with the fix for
every zone:

```text
                         displayedRatePercent
c2 as shipped            30        <- the bug
c2 with r1's change undone   3
c3 (the fix)             3
```

Of the 189 probe keys, the only ones that still differ are `ratePerMille`'s own
— which is the method whose unit the commit changed, and so cannot agree by
construction.

## Measured blame outcome at BFC^

The fix deletes exactly one line, and opens exactly one file:

```text
"return table.ratePerMille(zone);"   plain -> c2   -w -> c2   -w -C -C -> c2

git diff --name-only HEAD^ HEAD
  src/main/java/example/Shipment.java
```

Blame returns `{c2}` — half the answer. Nothing the fix touches points at
`SurchargeTable.java` at all.

## What a tool must do to pass

Report exactly `{r1, c2}`. Two steps are needed and they are independent:
following the call in the fixed line into a file the fix never opens, and then
choosing between two commits with the same subject, the same patch and the same
author date — only one of which is an ancestor of the fix. Reporting `c1` names
a commit that is not in the fix's history at all; the scenario declares it
`related_but_not_correct` so that answer is scored as wrong rather than
partially right.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

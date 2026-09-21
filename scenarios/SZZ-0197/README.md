# SZZ-0197: Extracted methods take ownership of an earlier faulty comparison

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `extract-method`, `behaviour-preserving-rewrite`, `tangled-bfc`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c5` · BFC `c6` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. Here a
behaviour-preserving **extract-method** refactoring becomes the author of the
first fault's line — where [SZZ-0192](../SZZ-0192/README.md) extracts locals
inside the same method, this moves the comparison into a method of its own,
which is then renamed, so following it back means matching an extraction rather
than a line.

## Commit structure

```text
c0  Add the discount eligibility check            age >= 18 && purchases >= 3
c1  Offer the discount to customers over eighteen age > 18                       <- BIC
c2  Note what the discount requires               class comment only (distractor)
c3  Split the eligibility test into named checks  oldEnough / frequentEnough (rewrite)
c4  Give the purchase-count check a clearer name  frequentEnough -> hasEnoughPurchases
c5  Require more than three purchases             purchases > 3                  <- BIC
c6  Accept eighteen-year-olds and three purchases again   both comparisons restored  <- BFC
```

`c3` moves `age > 18` out of `eligible` and into `oldEnough`, and in doing so
becomes the commit that wrote that line. `c4` renames the other helper, so the
line the second fault later edits has also been through a rename.

## Expected BIC / BFC

- BICs: `c1` and `c5` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c6`

## Measured behaviour (from the generated repository)

A driver sweeps ages 15–21 against 0–6 purchases, the boundaries the test turns
on. Per commit, how many of the 49 answers change:

```text
c0  Add the discount eligibility check            49 probes
c1  Offer the discount to customers over eighteen 4 change    eligible(18,3..6): true -> false
c2  Note what the discount requires               0 change
c3  Split the eligibility test into named checks  0 change    <- behaviour-preserving
c4  Give the purchase-count check a clearer name  0 change    <- behaviour-preserving
c5  Require more than three purchases             3 change    eligible(19..21,3): true -> false
c6  Accept eighteen-year-olds and three purchases again  7 change (all of them, restored)
```

Both faults are real and independent: `c1` costs the four eighteen-year-old
cases, `c5` the three three-purchase cases, and the fix restores exactly the
seven.

**This is a different kind of evidence from the interaction scenarios**, and it
is the right one here. In SZZ-0195, SZZ-0196, SZZ-0198 and SZZ-0199 the
unreachable commit is harmless alone, so undoing it on top of the faulty commit
reproduces the fixed behaviour. In a rewrite scenario that test fails by
construction, because the two commits are independent faults rather than a
prerequisite and its consumer. Measured: at `c5`, restoring only `age >= 18`
leaves `eligible(19, 3)` returning `false`, where the complete fix `c6` returns
`true` — `c5`'s fault is still there. Necessity here is shown by the two
faults' effects being disjoint and the fix repairing exactly their union.

## Measured blame outcome at BFC^

The fix deletes two lines:

```text
"return age > 18;"         plain -> c3   -w -> c3   -w -C -C -> c3
"return purchases > 3;"    plain -> c5   -w -> c5   -w -C -C -> c5
```

So blame returns `{c3, c5}`: it misses `c1` entirely and adds `c3`, a commit
that changed no behaviour — copy detection does not rescue it, because the
extracted line is new text rather than a copy of an existing one. The scenario
declares `tangled-bfc`, because the fix deletes a line owned by a commit that
is not a BIC.

## What a tool must do to pass

Report exactly `{c1, c5}`. `c3` must be rejected even though blame names it,
and `c1` must be reached through the extraction that moved its comparison.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

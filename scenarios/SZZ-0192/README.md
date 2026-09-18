# SZZ-0192: Blame lands on an equivalence-preserving rewrite and returns the wrong commit

## Purpose

The other scenarios in this tier make blame return *half* the answer. This one
makes it return a **wrong** commit: one of the lines the fix deletes was last
written by a behaviour-preserving rewrite, not by the commit that broke that
side of the check.

## Commit structure

```text
c0  Add the sensor reading window                  reading >= low && reading <= high
c1  Record the accepted window in the class comment comment only (distractor)
c2  Require readings above the low mark            reading > low                    <- BIC
c3  Split the window check into named parts        aboveLow / belowHigh locals (rewrite)
c4  Require readings below the high mark           belowHigh = reading < high       <- BIC
c5  Accept readings on both marks again            both comparisons restored        <- BFC
```

`c3` preserves behaviour exactly; it only names the two halves of the
condition. In doing so it becomes the author of the low-mark line.

## Expected BIC / BFC

- BICs: `c2` and `c4`; BFC: `c5`

## Measured blame outcome at BFC^

The fix deletes two lines:

```text
"boolean aboveLow = reading > low;"      plain -> c3    -w -> c3    -w -C -C -> c3
"boolean belowHigh = reading < high;"    plain -> c4    -w -> c4    -w -C -C -> c4
```

So blame returns `{c3, c4}`: it misses `c2` entirely and adds `c3`, a commit
that changed no behaviour. A tool that stops at the first blame result reports
a refactoring as a cause. The scenario declares `tangled-bfc`, because the fix
deletes a line owned by a commit that is not a BIC.

## What a tool must do to pass

Report exactly `{c2, c4}` — which needs the line history of the low-mark
comparison to be followed through the rewrite.

## Baseline outcome (measured)

No declared baseline solves it; the scenario is `tier: discriminating`.

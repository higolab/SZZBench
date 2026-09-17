# SZZ-0124: Variable rename after BIC

## Purpose

A behaviour-preserving rename rewrites the *faulty line itself*, so the line
that the bug-fixing commit deletes was last written by the refactoring
commit and not by the BIC. This is the case refactoring-aware SZZ exists
for: plain `git blame` misses the BIC.

The previous version of this scenario let the BFC restore the pre-rename
text, which undid the rename and made a textbook SZZ return
`{c1, c2}` — it measured BFC-side tangling instead of "refactoring after the
BIC" (issue #6). The BFC now keeps the rename and changes only the faulty
operator.

**SZZ-0125 is the matched control**: the same 4-commit shape with a rename
that does *not* touch the faulty line, where plain blame reaches the BIC.

## Commit structure

- `c0`: Adds `ReorderPlanner`, which computes the available stock as
  `onHandUnits - reservedUnits + inTransitUnits` and orders up to the
  reorder point plus the safety stock.
- `c1`: Subtracts the units in transit instead of adding them
  (`... - reservedUnits - inTransitUnits`), so the planner orders units that
  are already on their way. This is the BIC.
- `c2`: Renames the local `available` to `availableUnits` in all three lines
  that use it, including the faulty one. Behaviour-preserving.
- `c3`: Restores the `+ inTransitUnits` term **and keeps the new variable
  name**. This is the BFC; its diff is `+1 −1` in one hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor: it is what basic blame returns, but it did not introduce
the fault.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`int availableUnits = onHandUnits - reservedUnits - inTransitUnits;` — no
line added by `c2` is deleted. `git blame` at `c3^` on that line returns
**`c2`**, so the outcome is **miss**: the BIC is not reached and `c2` is
returned instead. `git blame -C -C` also returns **`c2`**: copy detection
does not help, because the line was rewritten in place rather than moved.
Consequently `szzbench generate` reports the informational finding
`W700: basic git blame reaches <c2>, not expected BIC(s) ['c1']`. That
finding is the designed property of this scenario, exactly as in SZZ-0081
and SZZ-0178, and not a defect.

## What a tool must do

To pass, a tool has to follow the line history through `c2` (TC-SZZ-style
`git log -L` / `blame` on the parent of the rename) or to recognise the
rename as behaviour-preserving (e.g. via a refactoring detector such as
RefactoringMiner or RefDiff) and continue to `c1`, where the faulty
sub-expression `onHandUnits - reservedUnits - inTransitUnits` first appears.
Returning `{c1, c2}` counts as a false positive
(`false_positives_allowed: []`).

## Behaviour check

`unitsToOrder` and `needsReorder` were probed over 875 input combinations:
`reorderPointUnits ∈ {0, 1, 10, 50, Integer.MAX_VALUE}` (constructor) and
`onHandUnits ∈ {0, 1, 5, 10, 60, 1000, Integer.MAX_VALUE}`,
`reservedUnits`, `inTransitUnits ∈ {0, 1, 5, 60, Integer.MAX_VALUE}`,
including the combinations in which the subtraction overflows. `c1` differs
from `c0` in 546 of them, and `c3` agrees with `c0` in all 875 — the rename
of `c2` survives in the fixed code without changing behaviour.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `variable-rename-after-bic`
- `basic-blame-distractor`

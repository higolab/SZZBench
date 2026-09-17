# SZZ-0127: Method signature extension after BIC

## Purpose

The refactoring between BIC and BFC turns a hard-coded threshold into a
method parameter: `qualifies(int quantity)` becomes
`qualifies(int quantity, int minQuantity)` and the body reads the parameter
instead of the constant. That rewrites the faulty line, so plain `git blame`
at the BFC parent stops at the signature change and misses the BIC. The
bug-fixing commit repairs the faulty term **inside the extended signature**
and does not revert the parameterisation.

Two defects of the previous version are repaired: the code did not compile
(the identifier `min` was never declared, issue #10), and the "signature
extension" commit also renamed the method and dropped a parameter, so the
scenario did not isolate the titled factor (issue #5). `c2` now changes the
signature and the call site and nothing else.

## Commit structure

- `c0`: Adds `BulkDiscountRule` with `qualifies(quantity)` (threshold
  `DEFAULT_MIN_QUANTITY = 10`) and `missingUnits(quantity)`.
- `c1`: Subtracts one unit before the comparison
  (`quantity - 1 >= DEFAULT_MIN_QUANTITY`), so an order line that is exactly
  at the threshold no longer qualifies. This is the BIC.
- `c2`: Extends the signature to `qualifies(int quantity, int minQuantity)`,
  replaces the constant in the body with the new parameter and passes
  `DEFAULT_MIN_QUANTITY` at the one existing call site. Behaviour-preserving
  for that call site; the faulty `quantity - 1` survives.
- `c3`: Removes the `- 1` and keeps the two-parameter signature. This is the
  BFC; its diff is `+1 −1` in one hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor: it is what basic blame returns, but it did not introduce
the fault.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`return quantity - 1 >= minQuantity;` — the signature line that `c2` added
is *not* deleted. `git blame` at `c3^` on the deleted line returns **`c2`**,
so the outcome is **miss**. `git blame -C -C` also returns **`c2`**: the
line was rewritten in place, so copy detection has nothing to follow.
`szzbench generate` therefore reports the informational finding
`W700: basic git blame reaches <c2>, not expected BIC(s) ['c1']`, which is
the designed property of the scenario (as in SZZ-0081 and SZZ-0178), not a
defect.

## What a tool must do

To pass, a tool has to follow the line history through `c2` or to recognise
the parameterisation as behaviour-preserving (a "change method signature" /
"parameterize" refactoring) and continue to `c1`, where `quantity - 1` first
appears. Returning `{c1, c2}` counts as a false positive
(`false_positives_allowed: []`).

## Behaviour check

The API changes legitimately at `c2`, so the probe uses the contract
`qualifies(q, DEFAULT_MIN_QUANTITY) ≡ qualifies(q)` with
`DEFAULT_MIN_QUANTITY = 10`, plus `missingUnits(q)`, which keeps its
signature. Inputs:
`quantity ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 8, 9, 10, 11, 12, 100, MAX_VALUE-1, MAX_VALUE}`.
`c1` differs from `c0` on 2 of the 13 inputs (`quantity == 10`, the
threshold itself, and `Integer.MIN_VALUE`, where `quantity - 1` underflows);
`c2` reproduces `c1` exactly, which confirms that the signature extension is
behaviour-preserving; `c3` agrees with `c0` on all 13.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `method-signature-change-after-bic`
- `basic-blame-distractor`

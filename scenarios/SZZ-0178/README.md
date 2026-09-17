# SZZ-0178: Faulty line rewritten twice before the fix (depth-2 line history)

## Purpose

This scenario checks whether an SZZ implementation can follow the history of
a faulty line through *two* behaviour-preserving rewrites. Single re-edits
already exist in the suite (SZZ-0081, SZZ-0083); here the BIC is two steps
away from what plain blame returns. SZZ-0179 is the matched control with the
same history shape in which the last rewrite *is* the BIC, so simply "going
deeper" is not a safe strategy.

## Commit structure

- `c0`: Adds `ShippingCostCalculator.cost(...)` taking the parcel weight in
  kilograms.
- `c1`: Switches the parameter to grams and computes the billable weight with
  integer division (`weightGrams / 1000`), so 1500 g are billed as 1 kg.
  This is the BIC.
- `c2`: Renames the local `total` to `amount` (three lines, including the
  faulty one). Behaviour-preserving.
- `c3`: Adds explicit parentheses to the same line. Behaviour-preserving.
- `c4`: Rounds up to the next started kilogram
  (`(weightGrams + 999) / 1000`). This is the BFC.

## Expected behavior

The expected BFC is `c4` and the expected BIC is `c1`. `c2` and `c3` are
known distractors.

## Plain blame outcome

`git diff -U0 c4^ c4` deletes one line. `git blame` at `c4^` on that line
returns **`c3`**: plain blame misses the BIC. Tracing the deleted line one
step further (the line `c3` replaced) reaches `c2`; tracing it a second time
reaches `c1`. `git blame -w` does not help because neither rewrite is
whitespace-only.

## What a tool must do

To pass, a tool has to trace the line history recursively (TC-SZZ-style) or
to recognise `c2` and `c3` as behaviour-preserving edits (rename, added
parentheses) and continue past them, stopping at `c1`, where the faulty
sub-expression `weightGrams / 1000` first appears.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `deep-line-history`
- `rewrite-depth-2`
- `basic-blame-distractor`

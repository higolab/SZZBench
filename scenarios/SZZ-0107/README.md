# SZZ-0107: Large commit with small bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `large-bic`, `tangled-bic` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks how an SZZ implementation reports a fault that sits
inside a genuinely large commit. The bug-introducing commit is a single
`+103 -1` change that implements discount, tax, rounding, shipping and payment
arithmetic and, on the way, tightens one pre-existing comparison by one
character. The one character is the declared fault; the other 102 added lines
are unrelated to it and are still in the tree at HEAD.

Commit-level SZZ is not the hard part here — plain `git blame` finds `c1`.
What the scenario exposes is everything a tool does *with* that commit: a
size-based filter that discards large commits as refactorings, an SZZ variant
that widens the answer to every line of the BIC, or a line-level evaluation
that has to pick one line out of 103.

## Commit structure

- `c0`: Adds `com.example.billing.InvoiceTotals` with `subtotalCents()` and
  `qualifiesForFreeShipping(int)` (`return subtotalCents >= thresholdCents;`).
  16 lines.
- `c1`: Adds `discountCents`, `netCents`, `taxCents`, `grossCents`,
  `roundToFiveCents`, `shippingCents`, `payableCents`, `lineItemCents`,
  `remainingToPayCents`, `isSettled`, `formatAmount`, `summary` and the private
  `clampToInt` helper, and changes the free-shipping comparison to
  `return subtotalCents > thresholdCents;`. This is the **BIC**; its
  first-parent diff is `+103 -1` on one file. The new `shippingCents` uses the
  faulty comparison, so the fault propagates into the code added by the same
  commit.
- `c2`: Restores `subtotalCents >= thresholdCents`. This is the **BFC**; its
  first-parent diff is `+1 -1`.

There is no intermediate commit in this scenario.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Measured plain-blame outcome at BFC^

`git diff -U0 c2^ c2` deletes exactly one line,
`        return subtotalCents > thresholdCents;` (line 15). `git blame` and
`git blame -w` at `c2^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Return `{c1}` and, at line level, the single deleted comparison. Ways to fail:
treat `c1` as too large to be a bug-introducing commit and fall back to `c0`;
report every line `c1` touched as faulty; or attribute the fault to the file
creation in `c0`, which did contain the method but with the correct bound.

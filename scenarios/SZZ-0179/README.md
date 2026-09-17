# SZZ-0179: Last of two rewrites of a line is the BIC (control for depth-2 line history)

## Purpose

Matched control for SZZ-0178. The repository has the same file, the same
five commits with the same messages, authors and shape of diffs, and the
same BFC. The difference is *where* the fault enters: in SZZ-0178 the first
rewrite of the formula (`c1`) is faulty and the two later rewrites preserve
it; here `c1` is correct and the last rewrite (`c3`, the "make precedence
explicit" cleanup) silently drops the round-up term. A tool that always
follows the line history back to its origin reports `c1` (and possibly
`c2`), which are false positives here.

The domain is deliberately shared with SZZ-0178 so that the two scenarios
differ only in the oracle-relevant content of `c1` and `c3`.

## Commit structure

- `c0`: Adds `ShippingCostCalculator.cost(...)` taking the weight in
  kilograms.
- `c1`: Switches the parameter to grams and correctly rounds up to the next
  started kilogram (`(weightGrams + 999) / 1000`).
- `c2`: Renames the local `total` to `amount`. Behaviour-preserving.
- `c3`: Adds explicit parentheses and, while doing so, drops `+ 999`, so
  1500 g are billed as 1 kg. This is the BIC.
- `c4`: Restores the round-up. This is the BFC.

## Expected behavior

The expected BFC is `c4` and the expected BIC is `c3`. `c1` and `c2` are
known distractors for tools that trace line history too far.

## Plain blame outcome

`git diff -U0 c4^ c4` deletes one line. `git blame` at `c4^` on that line
returns **`c3`**: exact.

## What a tool must do

To pass, a tool must stop at `c3`. Recursive line-history tracing has to
compare the semantics of successive versions of the line (the `+ 999` term
disappears in `c3`) instead of skipping every commit that looks like a
cleanup.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `deep-line-history`
- `matched-control`
- `last-rewrite-is-bic`

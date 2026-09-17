# SZZ-0183: Two-file BFC whose second hunk blames a non-BIC commit

## Purpose

The existing multi-file BFC scenario (SZZ-0122) only *adds* a file. Here the
BFC modifies two existing files, and the two hunks have different origins:
the hunk in `CurrencyConverter.java` replaces the BIC's line, the hunk in
`PriceDisplay.java` replaces a line that a later feature commit wrote. A tool
that reports the blame of every deleted line produces one false positive.

## Commit structure

- `c0`: Adds `CurrencyConverter` (rounds with `Math.round`) and
  `PriceDisplay`.
- `c1`: Replaces `Math.round(amountCents * rate)` with a plain `(long)`
  cast, truncating converted amounts. This is the BIC.
- `c2`: Changes the price format string in `PriceDisplay.format` so the
  currency code comes first. Unrelated to the fault.
- `c3`: Restores `Math.round` in `CurrencyConverter` and, in the same
  commit, changes the separator in `PriceDisplay.format` to a non-breaking
  space. This is the BFC. Its diff is `+2 -2` across two files.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2`
is a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes two lines. `git blame` at `c3^` returns
**`c1`** for the line in `CurrencyConverter.java` and **`c2`** for the line
in `PriceDisplay.java`: the BIC is reached, with one extra candidate.

## What a tool must do

To pass, a tool must separate the fix hunk from the tangled hunk, for
example by relating the commit message ("round converted amounts") to the
`CurrencyConverter` change, by noticing that the `PriceDisplay` change is a
string-literal-only edit, or by scoring candidates per hunk instead of
taking the union.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `multi-file-bfc`
- `tangled-bfc`

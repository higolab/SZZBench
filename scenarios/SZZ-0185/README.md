# SZZ-0185: BFC deletes comment and blank lines of a distractor together with the faulty line

## Purpose

This scenario tests the cosmetic-line filters of MA-SZZ/RA-SZZ-style tools.
The bug-fixing commit deletes three lines in one hunk: a blank line and a
comment line inserted by a distractor commit, and the faulty statement
written by the BIC. Without a filter for blank and comment-only lines the
distractor becomes a false positive.

## Commit structure

- `c0`: Adds `RetryBackoff.delayMillis(...)` without a delay cap.
- `c1`: Caps the delay, but uses `Math.max` instead of `Math.min`, so the
  delay is never shorter than the configured maximum. This is the BIC.
- `c2`: Inserts a blank line and the comment
  `// The cap keeps a long outage from stalling the worker for hours.`
  directly above the faulty `return`. Cosmetic only.
- `c3`: Replaces `Math.max` with `Math.min` and removes the blank and
  comment lines. This is the BFC. Its diff is `+1 -3`.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes three lines. `git blame` at `c3^` returns
**`c2`** for the blank line, **`c2`** for the comment line and **`c1`** for
the faulty statement: the BIC is reached, with one extra candidate.

## What a tool must do

To pass, a tool must ignore deleted lines that are blank or comment-only
before blaming (or discard candidates that are only reached through such
lines).

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `cosmetic-line-noise`

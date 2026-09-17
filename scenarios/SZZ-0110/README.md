# SZZ-0110: Large noisy intermediate history

## Purpose

This scenario checks that a *large* intermediate change to the faulty file
does not disturb bug-introducing-commit identification. Between the BIC and
the BFC, one commit adds 27 lines (four column-layout helpers) to the file
that holds the fault, and the fix touches none of them.

It is an honest **control**: plain `git blame` solves it. Its value is the
ratio between the intermediate change (`+27 -0`) and the fix (`+1 -1`): a tool
that ranks candidates by recency, by lines touched, or by "how much of this
file changed since" gets `c2` instead of `c1`.

## Commit structure

- `c0`: Adds `com.example.text.LabelFormatter` with `hasLabel(String)`
  (`return value != null;`) and `format(String)`, which trims a present label
  and returns `""` otherwise.
- `c1`: Changes the check to `return value == null;`. This is the **BIC**:
  `format()` returns `""` for every label that *was* supplied and throws
  `NullPointerException` for a missing one.
- `c2`: Adds `padRight`, `truncate`, `column` and `rule`. Its diff is
  `+27 -0`; it does not touch the faulty method.
- `c3`: Restores `value != null`. This is the **BFC**; its first-parent diff is
  `+1 -1` and all 27 helper lines stay in the file.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return value == null;` (line 5). `git blame` and `git blame -w` at
`c3^` both attribute that line to `c1`. No line added by `c2` is deleted by
the BFC.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Blame the one deleted line and stop. A tool fails by adding `c2`, which is the
most recent and by far the largest commit on the file between the BIC and the
fix.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `large-noisy-intermediate`

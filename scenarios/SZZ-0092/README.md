# SZZ-0092: Loop to conditional rewrite after BIC

## Purpose

This scenario checks how SZZ implementations behave when a behaviour-preserving
refactoring between the BIC and the BFC replaces a loop with a conditional and
carries the faulty comparison into the rewritten line. The bug-fixing commit
repairs the comparison *in the form it has at the BFC parent*; it does not undo
the refactoring.

## Commit structure

- `c0`: Adds `AttachmentName` with `extension(String)` (a backwards scan for the
  last `.`, returning the text after it) and `hasExtension(String)`.
- `c1`: Changes the scan bound from `index >= 0` to `index > 0` so that a dot at
  position 0 is skipped. This is the BIC: `".bashrc"` now reports no extension.
- `c2`: Replaces the backwards scan with `String.lastIndexOf('.')` and an
  `if (index > 0)` conditional. The rewrite is behaviour-preserving with respect
  to `c1` and moves the faulty comparison onto a new line.
- `c3`: Changes that conditional to `if (index >= 0)`. This is the BFC. Its
  first-parent diff is `+1 -1` on a single line.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`if (index > 0) {`). `git blame` at
`c3^` on that line returns **`c2`**: plain blame **misses** the BIC. `git blame -w`
does not help, because `c2` is not a whitespace-only change.

## What a tool must do

To pass, a tool has to follow the line history past the refactoring: one step
back from `c2` the same comparison is the bound of the `for` header written by
`c1`. Recognising `c2` as behaviour-preserving (a loop replaced by an equivalent
library call plus conditional), or searching the history for the comparison
`index > 0` (`git log -S`), both lead to `c1`.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`.
- Behaviour probe over 26 fixed attachment names (empty, `"."`, `".."`, `"..."`,
  `".bashrc"`, `"notes"`, `"notes."`, `"report.txt"`, `"archive.tar.gz"`,
  `"a.b.c"`, non-ASCII, …) plus a 300-character name with the single dot placed
  at every position 0…299: the `c1` snapshot differs from `c0` for every name
  whose only dot is at position 0 (4 of the fixed inputs and position 0 of the
  generated family), and the `c3` snapshot agrees with `c0` on all 326 probe
  outputs.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `loop-rewrite-after-bic`
- `basic-blame-distractor`

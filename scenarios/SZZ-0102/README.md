# SZZ-0102: Import reorder after BIC

## Purpose

This scenario checks that a pure import *reorder* between the BIC and the BFC
does not disturb bug-introducing-commit identification. The file already has
four imports when the bug is introduced; the intermediate commit sorts them
and adds or removes nothing, which is what an IDE "organize imports" action
produces.

It is an honest **control**: plain `git blame` solves it. Its value is to
separate tools that follow the faulty line from tools that add any commit
which touched the file after the BIC.

## Commit structure

- `c0`: Adds `com.example.orders.OrderIndex` with four imports in
  non-alphabetical order (`List`, `Comparator`, `ArrayList`, `Collections`)
  and the methods `add`, `sortedCodes`, `isTracked` and `codeAt`.
  `isTracked` is `return index >= 0 && index < codes.size();`.
- `c1`: Changes the lower bound to `return index > 0 && index < codes.size();`.
  This is the **BIC**: the first stored order code is now reported as
  untracked and `codeAt(0)` returns `null`.
- `c2`: Sorts the four imports alphabetically (`ArrayList`, `Collections`,
  `Comparator`, `List`). Git reduces the reorder to `+2 -2`, all inside the
  import block; no import is added or removed and no statement changes.
- `c3`: Restores `index >= 0`. This is the **BFC**; its first-parent diff is
  `+1 -1`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return index > 0 && index < codes.size();` (line 22). `git blame`
and `git blame -w` at `c3^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Blame the deleted line and stop. A tool fails by adding `c2`, for example
because it is the latest commit on the file or because a file-level (rather
than line-level) change model treats the reordered import block as part of the
fix's context.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `import-reorder-after-bic`

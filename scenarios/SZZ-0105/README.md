# SZZ-0105: Dead code addition after BIC

## Purpose

This scenario checks that code added between the BIC and the BFC, which is
never executed and is *not removed by the fix*, does not disturb
bug-introducing-commit identification. The intermediate commit adds a constant
and a private method that nothing calls; both are still in the file at HEAD.

It is an honest **control**: plain `git blame` solves it. Its value is that the
dead code survives the fix, so a tool cannot be rewarded for the accident that
the BFC happened to delete it.

## Commit structure

- `c0`: Adds `com.example.inventory.StockLevel` with `isAvailable(int)`
  (`return onHand >= requested;`) and `remainingAfter(int)`.
- `c1`: Changes the comparison to `return onHand > requested;`. This is the
  **BIC**: a request that exactly matches the stock on hand is refused,
  although `remainingAfter` correctly reports `0` for it.
- `c2`: Adds the constant `REORDER_POINT` next to the existing field and the
  private method `unitsBelowReorderPoint()` after `remainingAfter`. Nothing
  calls the method; the code is dead. Its diff is `+5 -0`, and neither hunk
  touches, re-indents or rewrites the faulty line.
- `c3`: Restores `onHand >= requested`. This is the **BFC**; its first-parent
  diff is `+1 -1` and it leaves the dead code in place.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return onHand > requested;` (line 12). `git blame` and `git blame -w`
at `c3^` both attribute that line to `c1`.

Blame class: **exact** — B-SZZ returns `{c1}`, which is the expected set.

## What a tool must do

Blame the deleted line and stop. A tool fails by adding `c2` because it is the
most recent commit on the file, or because a file-level change model counts
every commit since the BIC that touched `StockLevel.java`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `dead-code-after-bic`

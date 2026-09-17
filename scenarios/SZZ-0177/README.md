# SZZ-0177: Deletion-only BIC removes a guard that an addition-only BFC restores

## Purpose

This scenario realizes the shape that SZZ-0078 to SZZ-0080 intended but did
not achieve because of re-indentation: the BIC *only deletes* lines and the
BFC *only adds* lines. There is no faulty line that survives from the BIC to
the BFC, so the BFC has no deleted line to blame, and the BIC has no added
line that a tool could match against the fix.

## Commit structure

- `c0`: Adds `Account` and `TransferService.transfer(...)` with three guards
  (non-positive amount, daily limit, insufficient funds).
- `c1`: Deletes the three-line non-positive-amount guard and changes nothing
  else. This is the BIC. Its diff is `+0 -3`; the remaining lines keep their
  indentation. A negative amount now passes the other two guards and moves
  money from `to` to `from`.
- `c2`: Unrelated addition of a getter for the daily limit.
- `c3`: Re-inserts the guard and changes nothing else. This is the BFC. Its
  diff is `+3 -0`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes no line, so `git blame` at `c3^` has nothing to
trace: **none** (ghost). Blaming the context lines around the added hunk
(`public void transfer(...) {` and `if (amountCents > dailyLimitCents) {`)
returns `c0`, which is also wrong.

## What a tool must do

To pass, a tool has to notice that the added lines previously existed in the
file and find the commit that removed them, e.g. with `git log -S` on the
guard text or by searching the file history for a deletion of the added
lines. Only `c1` deletes them.

## Factors

- `single-bic`
- `single-bfc`
- `deletion-only-bic`
- `addition-only-fix`
- `guard-removal`

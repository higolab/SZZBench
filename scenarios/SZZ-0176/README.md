# SZZ-0176: Addition-only fix for an unhandled enum branch

## Purpose

This scenario checks how SZZ implementations behave when the fault is an
unhandled case in an if-chain over an enum, and the bug-fixing commit is
*addition-only*. The BIC is the commit that added the incomplete logic, not
the commit that defined the enum.

## Commit structure

- `c0`: Adds the `ShipmentState` enum (`CREATED`, `PACKED`, `SHIPPED`,
  `DELIVERED`, `RETURNED`) and `ShipmentNotifier` with `subject(...)` and
  `shouldNotify(...)`; `shouldNotify` is true for every state except
  `CREATED`.
- `c1`: Adds `ShipmentNotifier.body(ShipmentState state)`, which returns a
  message for `PACKED`, `SHIPPED` and `DELIVERED` and falls back to `""` for
  everything else, including `RETURNED`. This is the BIC.
- `c2`: Unrelated change to `subject(...)` (store name in brackets).
- `c3`: Inserts the `RETURNED` branch before the fallback `return "";`. This
  is the BFC. Its diff is `+3 -0`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes no line, so `git blame` at `c3^` has nothing to
trace: **none** (ghost).

## What a tool must do

To pass, a tool has to attribute the added branch to the if-chain it extends,
for example by blaming the context lines of the added hunk (the closing brace
of the `DELIVERED` branch and `return "";`), both of which belong to `c1`.
Blaming `ShipmentState.java` instead leads to `c0`, which is wrong: the enum
constant existed before the incomplete logic was written.

## Factors

- `single-bic`
- `single-bfc`
- `omission-bug`
- `addition-only-fix`
- `missing-branch`

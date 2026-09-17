# SZZ-0182: Cross-file ghost: BIC deletes a validation call in one file, BFC adds a check in another

## Purpose

This scenario combines a deletion-only BIC with an addition-only BFC in a
*different file*. The BIC removes the call that validated orders before
payment; the BFC does not restore that call but hardens the payment gateway
instead. There is no line in either file that connects the fix to the BIC
through blame.

## Commit structure

- `c0`: Adds `Order`, `OrderValidator`, `PaymentGateway` and
  `CheckoutService.checkout(...)`, which validates the order and then
  charges it.
- `c1`: Deletes `validator.validate(order);` from `CheckoutService.checkout`
  and changes nothing else (`+0 -1`). Orders with a non-positive total are
  now charged. This is the BIC.
- `c2`: Unrelated change in `PaymentGateway.charge` (charge record includes
  the order id).
- `c3`: Adds a non-positive-total guard at the top of
  `PaymentGateway.charge` (`+3 -0`). This is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes no line, so `git blame` at `c3^` has nothing
to trace: **none** (ghost). Blaming the context lines of the added hunk in
`PaymentGateway.java` returns `c0` (method header) and `c0`/`c2`
(body), none of which is the BIC. The BIC's file, `CheckoutService.java`, is
not touched by the BFC at all.

## What a tool must do

To pass, a tool must reason beyond the BFC's file: the added check
re-establishes an invariant (`totalCents > 0`) that `OrderValidator.validate`
already enforced, and the commit that stopped calling the validator on this
path is `c1`. Searching the history for deletions of calls to
`validate(...)` (`git log -S`) or tracking which commit made
`PaymentGateway.charge` reachable with unvalidated orders both lead to `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `deletion-only-bic`
- `addition-only-fix`
- `cross-file-fix`

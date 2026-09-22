# SZZG-0120: Two branches that are each harmless, and a merge that is not

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bic`, `merge`, `guard-removal`, `caller-callee-interaction`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c4` |
| graph features | 2 branches; merge commit `c3`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. It is the
third instance of the *guard* kind — after
[SZZ-0193](../../scenarios/SZZ-0193/README.md) (the guard is deleted) and
[SZZ-0198](../../scenarios/SZZ-0198/README.md) (the guard substitutes a
different value) — and the first in which the two halves live on **different
branches**, so the bug exists in neither parent's tree and appears for the
first time in a merge that changed nothing itself.

## Commit structure

```text
*   a11fe41  Charge nothing when the credit covers the subtotal   <- BFC (c4)
*   ca3056d  Merge the loyalty branch                             (c3, no operations)
|\
| * 9ac5170  Apply a loyalty credit before the discount   new class, subtracts   <- BIC (c2, branch loyalty)
* | 49d2e01  Discount the subtotal without checking its sign   guard removed      <- BIC (c1, main)
|/
* ff9785a  Add the checkout discount                    guard rejects a negative subtotal (c0)
```

## Expected BIC / BFC

- BICs: `c1` and `c2` (`exact_set`, `required: [c1, c2]`)
- BFC: `c4`

## Measured behaviour: the bug is in neither parent

What each tree charges for a 1000-cent order at 10% off:

```text
                                      amountDue(1000,1000)  amountDue(1000,1500)  amountDue(1000,3000)
c1  main before the merge             CreditedCheckout is absent - the path does not exist
c2  loyalty branch tip                0                     0                     0
c3  the merge                         0                     -450                  -1800    <- the bug
c4  the fix                           0                     0                     0
```

On main after `c1` the guard is gone, but nothing in the repository produces a
negative subtotal: `discounted(-500, 10)` is already `-450`, and no caller ever
passes a negative value. On the loyalty branch after `c2` the subtraction
exists, but the guard is still there and catches its result. The merge puts the
subtraction and the missing guard in one tree, and an over-credited order is
refunded instead of charged nothing.

The merge `c3` carries no operations of its own — the two branches touch
different files — so the commit where the bug first exists is not a commit any
line-based method would examine.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return checkout.discounted(subtotalCents - creditCents, percentOff);"
    plain -> c2   -w -> c2   -w -C -C -> c2
```

Blame returns `{c2}` — half the answer. `c1` is in another file, on the other
side of the merge, and is not reachable from the deleted line by any blame
variant.

## What a tool must do to pass

Report exactly `{c1, c2}`, and not `c3`, the merge, which changed nothing.
Reaching `c1` means following the call in the fixed line into
`Checkout.discounted`, seeing that the subtraction can enter the range the
guard used to reject, and crossing to the other parent of the merge to find the
commit that removed it.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

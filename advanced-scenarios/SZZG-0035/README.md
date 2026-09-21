# SZZG-0035: One BIC causes multiple bug symptoms

## Purpose

One faulty helper, two symptoms, two fixes. `Fees.fee` computes a 3 percent
fee; `c1` writes 30. Both `cardFee` and `transferFee` call it, and each caller
is repaired by its own commit that computes the fee directly instead of calling
the helper. The scenario carries two bug entries with the same bug-introducing
commit, and the helper keeps its faulty constant at `HEAD` — it is simply no
longer called.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, one distractor on
the fault file, 4 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* 99671a4  2025-05-16  Compute the transfer fee directly in the remaining caller    <- BFC of B002 (c3)
* bf2ce46  2025-05-15  Compute the card fee directly instead of calling fee()       <- BFC of B001 (c2)
* f8fee52  2025-05-08  Apply the 3 percent fee                                      <- BIC of both (c1; writes 30)
* 5db0465  2025-05-01  Add the payment fee helpers                                  (c0)
```

## Expected BIC / BFC

- BIC: `c1` for both bugs (`exact_set`, `required: [c1]`; `bug_groups` records the shared root cause)
- BFCs: `c2` (B001, card fee), `c3` (B002, transfer fee)

## Measured behaviour and blame

| commit | `cardFee(1000)` | `transferFee(1000)` |
|---|---|---|
| `c0` | 30 | 30 |
| `c1` | **300** | **300** |
| `c2` | 30 | **300** |
| `c3` | 30 | 30 |

Each fix deletes one line, `return fee(cents);`, written by `c0` — not the
faulty helper line — so plain blame of the fixes' deleted lines returns `c0`,
the root commit, and does not reach `c1`. The verifier's fault-statement blame
(`return cents * 30 / 100;` at each fix's parent) does reach `c1` (`GI703`), and
it reports `GW664` for B002 because both callers end up with the same inlined
statement — as before the rewrite; this scenario has always been on the
strict-verify list for that reason.

## What a tool must do

Report `c1` for either fix. The fixes route around the fault rather than
editing it, so a tool that blames only deleted lines lands on `c0` and has to
look at what the deleted call *reached* — the helper `c1` changed — to find the
cause.

## Factors

- `root-cause`
- `wrong-constant`

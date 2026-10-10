# SZZ-0193: A widened precondition that only becomes a fault once a later commit can reach it

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `prerequisite-bic`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario whose unreachable commit is a **prerequisite**:
it widens what the code accepts, which is harmless until a later commit creates
a path that reaches the widened case.

## Commit structure

```text
c0  Add the spending budget check          rejects a negative cost, then compares to the limit
c1  Compare the cost against the limit directly   the negative guard is gone        <- BIC
c2  Name the budget limit in the class comment    comment only (distractor)
c3  Approve spending after a refund               withinBudget(cost - refund)       <- BIC
c4  Reject a refund larger than the cost          cost >= refund && withinBudget(...)  <- BFC
```

`c1` is harmless while every caller passes a non-negative cost. `c3` adds a
path that subtracts a refund and can therefore produce a negative amount, which
the removed guard would have rejected: a refund larger than the cost is now
approved.

## Expected BIC / BFC

- BICs: `c1` and `c3`; BFC: `c4`

Without `c1` the guard still rejects the negative amount, so the refund path
would be safe; without `c3` nothing produces a negative amount.

## Measured blame outcome at BFC^

```text
"return withinBudget(costCents - refundCents);"   plain -> c3   -w -> c3   -w -C -C -> c3
```

`c1` deleted the guard three commits earlier and owns nothing the fix touches,
so no blame variant reaches it. Finding it means reasoning about what the
repaired call can now pass, not about which lines changed.

## Baseline outcome (measured)

No declared baseline solves it; the scenario is `tier: discriminating`.

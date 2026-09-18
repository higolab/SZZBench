# SZZ-0196: An overload added earlier captures a call written later

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. The
unreachable commit added a **method overload**, so — unlike
[SZZ-0191](../SZZ-0191/README.md), where the called method's body changed —
reaching it means resolving *which* method the fixed line calls, not reading
the one whose name it spells.

## Commit structure

```text
c0  Add the money formatter and the receipt line   format(long cents); line() calls it
c1  Format amounts that are already whole units    adds overload format(int wholeUnits)  <- BIC
c2  Say which formatter takes which unit           class comment only (distractor)
c3  Show the receipt total                         adds total(int cents) -> format(cents)  <- BIC
c4  Format the receipt total as an amount in cents format((long) cents)                   <- BFC
```

`c1` adds an overload for amounts that are already whole units. The only call
in the repository at that point passes a `long`, so it keeps binding to
`format(long)` and nothing changes. `c3` adds a caller that passes an `int`
amount in cents; that is an exact match for the new overload, so a 250-cent
total prints as `250.00` instead of `2.50`.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

## Measured behaviour (from the generated repository)

Every public method of both classes called over a grid of arguments. Per
commit, how many **shared** probe keys change value, and how many keys appear:

```text
c0  Add the money formatter and the receipt line   2 probes
c1  Format amounts that are already whole units    changed 0, added 24   <- no existing answer moves
c2  Say which formatter takes which unit           changed 0, added 0
c3  Show the receipt total                         changed 0, added 24
c4  Format the receipt total as an amount in cents changed 23
```

`c1` adds reachable methods but moves no answer any existing call produces.

**Both commits are necessary, measured rather than argued.** Reverting `c1` on
top of `c3` — the tree in which the faulty call exists but the overload does
not — makes `total` agree with the fixed version exactly:

```text
                       total(1)   total(100)  total(1000)
c3 as shipped          1.00       100.00      1000.00      <- the bug
c3 with c1 reverted    0.01       1.00        10.00
c4 (the fix)           0.01       1.00        10.00
```

Without the overload the call widens to `format(long)`, which is what the fix
makes it do explicitly. Over the whole grid the counterfactual tree agrees with
the fix on **all 25** `Receipt` probe keys, with none differing.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return Money.format(cents);"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant. The two calls to `format` are written
differently (`amountCents` and `cents`) so the blamed line is unambiguous.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching `c1` means resolving the call in the fixed
line to the overload it selects, and finding the commit that introduced that
overload — a step no textual history operation performs.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

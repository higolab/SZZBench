# SZZ-0195: Scale change carried in stored state, and a later reader of the raw field

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `line-modification`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c4` · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. The
unreachable commit changed the **scale of a stored field**, so — unlike
[SZZ-0190](../SZZ-0190/README.md), where the changed value is a constant the
fixed expression names — reaching it means following a value through the
object's state rather than through a literal.

## Commit structure

```text
c0  Add the account ledger                    balance in yen
c1  Hold the ledger balance in sen            balance becomes long sen; deposit/balanceYen convert  <- BIC
c2  Record what the ledger stores             class comment only (distractor)
c3  Report whether the account is empty       adds isEmpty() (distractor)
c4  Charge a maintenance fee on the balance   adds feeYen() = balance * rate / 100                  <- BIC
c5  Charge the maintenance fee on yen, not sen  balance * rate / 10000                              <- BFC
```

`c1` converts the field and both of its accessors together. `c4` adds a method
that reads the field directly, as if it still held yen, so a 1% fee on a
1000-yen balance is charged as 1000 yen.

## Expected BIC / BFC

- BICs: `c1` and `c4` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c5`

## Measured behaviour (from the generated repository)

A driver deposits an amount and then asks the ledger what it reports, for nine
amounts and six rates. Per commit, the probe lines that differ from the
previous commit:

```text
c0  Add the account ledger                    9 probes
c1  Hold the ledger balance in sen            0 differ   <- behaviour-preserving
c2  Record what the ledger stores             0 differ
c3  Report whether the account is empty       0 differ
c4  Charge a maintenance fee on the balance   54 new probe lines (feeYen appears)
c5  Charge the maintenance fee on yen, not sen  40 answers change
```

So `c1` changes nothing any caller in the repository can observe, which is what
makes it invisible to a tool that looks only at the fix.

**Both commits are necessary, measured rather than argued.** Reverting `c1` on
top of `c4` — the tree in which the fault line exists but the scale change does
not — makes `feeYen` correct:

```text
with c1     feeYen(1) after deposit(1000) = 1000     (the bug: a 1% fee of 1000 yen)
without c1  feeYen(1) after deposit(1000) = 10       (correct)
```

That holds across the whole grid, not just at one argument: the counterfactual
tree agrees with the fix on **all 63** probe keys, with none differing.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return (int) (balance * ratePercent / 100);"   plain -> c4   -w -> c4   -w -C -C -> c4
```

Blame returns `{c4}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant.

## What a tool must do to pass

Report exactly `{c1, c4}`. Reaching `c1` means following the field
`balance` from the expression the fix repairs to the commit that changed what
the field holds.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

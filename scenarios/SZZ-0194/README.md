# SZZ-0194: The other bug-introducing commit is in a class the fix never touches

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `cross-file-bic`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario whose unreachable commit lives in a **different
file**. Every line the fix deletes is in `Invoice.java`; the change that makes
the new method wrong is in `TaxTable.java`, which the fix never opens.

## Commit structure

```text
c0  Add the tax table and the invoice total   rate() in percent, taxCents divides by 100
c1  Hold the tax rate in per-mille            rate() x10, taxCents divides by 1000   <- BIC
c2  Note where the invoice totals are used    class comment only (distractor)
c3  Show the tax rate on the invoice          adds displayedRatePercent() = rate()   <- BIC
c4  Show the tax rate as a percentage         rate() / 10                            <- BFC
```

`c1` converts the table and its only caller together, so the invoice totals are
unchanged: `taxCents` agrees with `c0` on all 168 probed `(amount, region)`
pairs, including `20_000_000` where an `int` product would overflow — the
multiplication is widened to `long` for exactly that reason. `c3` adds a method
that reports the raw table value as a percentage, and only then does the
invoice show 80% instead of 8%.

## Expected BIC / BFC

- BICs: `c1` and `c3`; BFC: `c4`

Without `c1` the table still holds percentages and the new method is correct;
without `c3` nothing reports the raw value.

## Measured blame outcome at BFC^

```text
"return table.rate(region);"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame stays inside `Invoice.java` and returns `{c3}`. `c1`'s change to
`TaxTable.java` is reachable only by following the call across the file
boundary — `-C -C` does not help, because nothing was copied or moved.

## Baseline outcome (measured)

No declared baseline solves it; the scenario is `tier: discriminating`.

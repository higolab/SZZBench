# SZZG-0145: The unit change is a regenerated five-thousand-line table the fix never opens

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `generated-file`, `non-source-file`, `config-bic`, `value-flow`, `config-value`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
| graph features | operation `write_generated_text_file`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in G8 (issue #35). It is the *file* kind
of the measured axis — the second commit is somewhere the fix never opens, as in
[SZZ-0199](../../scenarios/SZZ-0199/README.md) (a properties file) — with G8's
own theme on top: the file is a **generated, five-thousand-line table**, and
the commit that changed its unit rewrote every line of it. A tool that skips
large regenerated files as noise, or never leaves the Java file the fix
touched, has half the answer.

## Commit structure

```text
c0  Add the zone tariff table and its reader       zone-rates.csv in dollars (5,000 rows); rateCents() = value * 100
c1  Regenerate the zone tariff table in cents      every row rewritten (zone-N,N00); rateCents() = value   <- BIC
c2  Describe the zone table in the README          docs only (distractor)
c3  Show the tariff of a zone on the quote         rateLabel() = raw value + " USD"                       <- BIC
c4  Print the zone tariff in dollars on the quote  rateLabel() = rateCents() / 100 + " USD"               <- BFC
```

`c1`'s diff is 5,001 deletions and 5,001 insertions in `zone-rates.csv` — the
header `zone,rate_dollars` becomes `zone,rate_cents` and every row gains two
zeros — and one line of `ZoneRates.java`, where `rateCents()` stops multiplying.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`exact_set`, `required: [c1, c3]`)
- BFC: `c4`

Both are necessary. Without `c3` nothing prints the raw table value; without
`c1` the table is in dollars and `c3`'s label is right.

## Measured behaviour

`rateCents("zone-3")`, `rateCents("zone-1250")`, `rateLabel("zone-3")` and
`rateLabel("zone-1250")` at each commit (`tests/test_rebalance_scenarios.py`;
`rateLabel` exists from `c3`):

| commit | rateCents zone-3 | rateCents zone-1250 | rateLabel zone-3 | rateLabel zone-1250 |
|---|---|---|---|---|
| `c0`–`c2` | 300 | 125000 | — | — |
| `c3` | 300 | 125000 | **300 USD** | **125000 USD** |
| `c4` | 300 | 125000 | 3 USD | 1250 USD |

`c1` changes no answer: the table and its only reader change together.
**Counterfactual, measured:** undoing `c1` on top of `c3` — the table back in
dollars, `rateCents()` multiplying by 100 again — gives `3 USD` and `1250 USD`,
the fixed answers.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return rawRate(zone) + \" USD\";"    plain -> c3    -w -> c3    -w -C -C -> c3
```

Blame returns `{c3}`. `c1` is on no line the fix touches: its Java change is in
`rateCents()`, which the fix calls but does not edit, and its other 10,002
changed lines are in a CSV the fix never opens.

## What a tool must do to pass

Report exactly `{c1, c3}`. From the fixed expression a tool has to follow
`rawRate()` to the table it reads, and find the commit that changed what the
table's values mean — a commit whose diff is a regenerated file of five
thousand rows plus one Java line. Skipping that diff because it is large, or
because the file is not source, is the failure.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

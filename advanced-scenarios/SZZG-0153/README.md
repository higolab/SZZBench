# SZZG-0153: The unit lives in a binary table, and the commit that changed it has no line to blame

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `binary-file`, `non-source-bic`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
| graph features | operation `write_binary_file`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

G8's second `discriminating` scenario, after
[SZZG-0145](../SZZG-0145/README.md). Both put the unreachable half of the
answer in a file the fix never opens, and the files differ in the way that
matters. SZZG-0145's table is **text**: its diff is 5,001 deleted and 5,001
added lines, and a tool that reads it can attribute every row. This table is
**binary**: the change is twenty bytes for twenty bytes, git reports
`Bin 20 -> 20 bytes`, and the commit adds and deletes no line anywhere in the
repository.

## Commit structure

```text
c0  Add the zone tariff table and its reader   zone-rates.bin = "ZRTD" + 9, 12, 15, 20; rateCents honours the header
c1  Re-export the zone tariff table in cents   zone-rates.bin = "ZRTC" + 900, 1200, 1500, 2000   <- BIC
c2  Describe the zone tariff table             docs only (distractor)
c3  Show the tariff of a zone on the quote     rateLabel(zone) = rawValue(zone) + " USD"          <- BIC
c4  Print the zone tariff in dollars on the quote   rateCents(zone) / 100 + " USD"                <- BFC
```

The table is a four-byte header followed by one big-endian `int` per zone. The
header's fourth byte is the unit — `D` for dollars, `C` for cents — and
`rateCents` reads it, so the re-export changes the stored numbers and not the
rates.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`exact_set`, `required: [c1, c3]`)
- BFC: `c4`

Both are necessary. Without `c3` nothing prints a raw table value; without `c1`
the table is in dollars and `c3`'s label is right.

## Measured behaviour (from the generated repository)

`Quote.shippingCents` for all four zones and the label, at each commit
(`tests/test_graph_deepened_categories.py`):

| commit | `shippingCents(0..3)` | `rateLabel(0)` | `rateLabel(3)` |
|---|---|---|---|
| `c0` | 900, 1200, 1500, 2000 | — | — |
| `c1` | 900, 1200, 1500, 2000 | — | — |
| `c2` | 900, 1200, 1500, 2000 | — | — |
| `c3` | 900, 1200, 1500, 2000 | **"900 USD"** | **"2000 USD"** |
| `c4` | 900, 1200, 1500, 2000 | "9 USD" | "20 USD" |

Shipping costs the same cents throughout: the reader honours the header, so
`c1` moves nothing. `rawValue` is package-private, so `shippingCents` and
`rateCents` are the whole public surface until `c3` adds the label.

## Measured blame outcome at BFC^

```text
Quote.java  "return rates.rawValue(zone) + \" USD\";"  plain -> c3  -w -> c3  -w -C -C -> c3
ZoneRates.java  "return table[3] == 'C' ? ..."        plain -> c0  -w -> c0  -w -C -C -> c0
```

Blame returns `{c3}`. The unit check itself belongs to `c0`, where it was
written, so following the accessor the fixed line calls leads to the initial
commit rather than to `c1`.

What `c1` leaves behind is measured too, and it is less than nothing to read:

```text
git diff c0 c1 -- src/main/resources/zone-rates.bin   ->  Bin 20 -> 20 bytes, 0 insertions, 0 deletions
git blame c1 -- src/main/resources/zone-rates.bin     ->  c1, with all twenty bytes as line 1
```

Blaming the file does name `c1` — git treats a binary file as one line — but it
names it for the whole table at once, which says the table was re-exported and
not that its unit changed. The fourth byte is what turns that into the answer.

## What a tool must do to pass

Report exactly `{c1, c3}`. `c3` is blame's answer. Reaching `c1` means
considering a commit whose diff adds and deletes no line, and then reading the
file rather than the diff: the accessor the fixed line calls reads
`zone-rates.bin`, and the byte that decides the unit changed there.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

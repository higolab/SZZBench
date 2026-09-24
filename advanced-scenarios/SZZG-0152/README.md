# SZZG-0152: The fix message names a release, and only the changelog of that release says what changed

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `release-tag`, `non-source-evidence`, `refactoring-after-bic`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c4` · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
| graph features | ref lifecycle; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

G7's second `discriminating` scenario, after
[SZZG-0144](../SZZG-0144/README.md). Both put the evidence outside the diff,
and the forms differ. SZZG-0144's evidence is an **issue document** the fix
message names, and following the constant would reach the unreachable commit
anyway. Here the value-flow route is **closed**: a rename owns the constant's
line, so a tool that follows the value stops at a commit that only renamed it.
So is the message route: no commit says which unit anything is in except the
fix itself. What is left is the fix message's release name, the tag that says
which three commits the release contains, the changelog section written under
it, and a choice among those three.

## Commit structure

```text
c0  Add metering and its changelog         UNIT_PRICE = 12; costCents = units * UNIT_PRICE; CHANGELOG 2.3.0   (tag v2.3.0)
c1  Add finer price bands to metering      UNIT_PRICE = 120; costCents divides by ten                 <- BIC
c2  Name the metering price after what it prices  rename to METERED_UNIT_PRICE                        (rewrite)
c3  Release 2.4.0                          VERSION; the CHANGELOG entry for 2.4.0                     (tag v2.4.0)
c4  Show the metering price on the invoice  priceLabel() = METERED_UNIT_PRICE + " cents per unit"      <- BIC
c5  Show the metering price in cents, as it has been held in tenths since v2.4.0   / 10 in the label   <- BFC
```

The history is linear. `git log v2.3.0..v2.4.0` lists `c1`, `c2` and `c3`, and
the changelog section `## 2.4.0`, written by the release commit `c3`, says what
the release did:

```text
- The metering unit price is held in tenths of a cent. Callers that read
  the constant must divide by ten.
```

`c1`'s own subject says only that finer price bands were added, so neither
`git log --grep` nor the changelog names it: the entry belongs to the release,
and choosing between the release's three commits is part of the work.

## Expected BIC / BFC

- BICs: `c1` and `c4` (`exact_set`, `required: [c1, c4]`)
- BFC: `c5`

Both are necessary. Without `c4` nothing prints the constant; without `c1` the
price is 12 and `c4`'s label is right.

## Measured behaviour (from the generated repository)

`costCents` at one unit, twenty-five units and the top of the supported domain,
and the label, at each commit (`tests/test_graph_deepened_categories.py`):

| commit | `costCents(1)` | `costCents(25)` | `costCents(17 895 697)` | `priceLabel` |
|---|---|---|---|---|
| `c0` | 12 | 300 | 214748364 | — |
| `c1` | 12 | 300 | 214748364 | — |
| `c2` | 12 | 300 | 214748364 | — |
| `c3` | 12 | 300 | 214748364 | — |
| `c4` | 12 | 300 | 214748364 | **"120 cents per unit"** |
| `c5` | 12 | 300 | 214748364 | "12 cents per unit" |

A metered unit costs twelve cents throughout: `c1` multiplies the constant by
ten and divides the one reader by ten in the same commit, and `c2` renames it.
Only the label is wrong, from `c4` until `c5`.

## Measured blame outcome at BFC^

```text
"return METERED_UNIT_PRICE + \" cents per unit\";"  plain -> c4  -w -> c4  -w -C -C -> c4
"static final int METERED_UNIT_PRICE = 120;"        plain -> c2  -w -> c2  -w -C -C -> c2
"return units * METERED_UNIT_PRICE / 10;"           plain -> c2  -w -> c2  -w -C -C -> c2
```

Blame returns `{c4}`. Every line that carries the value belongs to `c2`, the
rename, so following the constant does not reach `c1` either. `c1` is named by
no line of the Java file at the fix.

## The evidence a tool can use

The fix's message is *"Show the metering price in cents, as it has been held in
tenths since v2.4.0"*. `v2.4.0` is a tag; the commits it added over `v2.3.0`
are `c1`, `c2` and `c3`; and the changelog section that release wrote says the
unit changed and that callers reading the constant must divide by ten. Of the
three commits in the range, `c2` and `c3` are a rename and a release commit, so
`c1` is the only one that could have changed it.

Measured, and the point of the design: `git log --all --grep` for *cent* or
*tenth* returns the fix and nothing else, and `git log -S"tenths"` returns `c3`,
the commit that wrote the changelog entry — not the commit the entry is about.
An earlier revision of this scenario subjected `c1` *"Hold the metering price in
tenths of a cent"*, which handed a grep the answer and made the release name
decorative (PR #87 review).

## What a tool must do to pass

Report exactly `{c1, c4}`. `c4` is blame's answer. Reaching `c1` means
resolving a release name to the commits a tag contains, reading a changelog
written outside the source, and then deciding which of those commits the entry
describes — the value leads only to the commit that renamed it, and the
messages say nothing.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

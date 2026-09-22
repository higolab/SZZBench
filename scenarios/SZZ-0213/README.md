# SZZ-0213: A tangled three-hunk fix: one hunk blames a bystander, one repairs an omission by adding lines

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `tangled-bfc`, `multi-hunk-bfc`, `mixed-origin-hunks`, `wrong-operator`, `null-check-omission`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S4 (issue #35). S4's controls each
show one way the *fix's* shape misleads blame — a multi-hunk fix whose hunks
blame different commits ([SZZ-0186](../SZZ-0186/README.md)), a fix that deletes
a distractor's lines together with the fault ([SZZ-0185](../SZZ-0185/README.md)).
Here one fix does both at once, and one of the two faults it repairs is an
omission whose hunk deletes nothing. Blame on what the fix deletes returns one
right commit, one bystander, and cannot reach the second fault at all.

## Commit structure

```text
c0  Add the invoice total with tax                netCents * TAX_PERCENT / 100; an unused legacy constant
c1  Reorder the tax arithmetic                    netCents / 100 * TAX_PERCENT  (divides first, truncates)   <- BIC
c2  Add the customer record with its loyalty tier Customer.java (distractor)
c3  Grant gold customers a tenth off              discountCents() dereferences customer without a null check   <- BIC
c4  Multiply before dividing in the tax, skip the discount for anonymous customers, drop the legacy rounding step   <- BFC
```

`c4` has three hunks in `InvoiceTotal.java`: it deletes the legacy constant and
its comment (a cleanup; the constant is read nowhere), restores the order of the
tax arithmetic, and adds `if (customer == null) return 0;` above the
dereference `c3` wrote.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

## Measured behaviour

`withTaxCents(1999)`, `withTaxCents(2000)`, and `discountCents(customer, 1000)`
for a gold, a standard and an anonymous (`null`) customer, at each commit
(`tests/test_rebalance_scenarios.py`; `discountCents` exists from `c3`):

| commit | tax on 1999 | tax on 2000 | gold | standard | anonymous |
|---|---|---|---|---|---|
| `c0` | 2198 | 2200 | — | — | — |
| `c1` | **2189** | 2200 | — | — | — |
| `c2` | 2189 | 2200 | — | — | — |
| `c3` | 2189 | 2200 | 100 | 0 | **NullPointerException** |
| `c4` | 2198 | 2200 | 100 | 0 | 0 |

Ten percent of 1999 cents is 199 after truncation, so the total is 2198; `c1`
divides first, `1999 / 100 = 19`, and adds 190. Whole-euro amounts are
unaffected. The two faults are independent, and the partial fix measured at
`c3` shows both are necessary: fixing only the tax leaves the anonymous
customer throwing, adding only the null check leaves the total at 2189.

## Measured blame outcome at BFC^

The fix deletes four lines, one of them blank:

```text
"/** Rounding step of the 2023 statements; kept until the archive export is retired. */"   plain -> c0   -w -> c0   -w -C -C -> c0
"static final int LEGACY_ROUNDING_CENTS = 5;"                                             plain -> c0   -w -> c0   -w -C -C -> c0
""                                                                                        plain -> c0   -w -> c0   -w -C -C -> c0
"return netCents + netCents / 100 * TAX_PERCENT;"                                         plain -> c1   -w -> c1   -w -C -C -> c1
```

The null-check hunk adds three lines and deletes none. Blame therefore returns
`{c0, c1}`: `c1` is right; `c0`, the initial commit, is a bystander whose
obsolete constant the fix happened to remove; `c3` is on no deleted line.

## What a tool must do to pass

Report exactly `{c1, c3}`. `c0` has to be rejected: the lines that blame to it
are a cleanup hunk, and the constant they declare is read nowhere. `c3` has to
be reached through the hunk that deletes nothing: the added guard protects a
dereference of `customer`, and the commit that wrote that dereference without a
guard is the answer. Separating the hunks of a tangled fix by purpose — repair,
repair, cleanup — is the step blame does not take.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

# SZZ-0225: The wrong expectation was written into a test first, and a rename inside the test took ownership of it

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `test-only-bic`, `test-line-noise`, `multi-file-bfc`, `refactoring-after-bic`, `candidate-selection-distractor`, `off-by-one`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S8's second `discriminating` scenario, after
[SZZ-0199](../SZZ-0199/README.md), which hides its unreachable commit in a
properties file. Here the fault begins as an *expectation*: a test edited to
want one day fewer than the fee charges, which a later commit then satisfies by
changing the product. A rename of the test's helper between them takes ownership
of the expectation's line, so blame reaches the product change and the rename
but not the commit that started it.

A test-only BIC is not new to the suite — [SZZ-0170](../SZZ-0170/README.md) is
a `control` with one — but there the fix edits the very expectation the BIC
wrote, so blame names it directly. What is new here is that the test-only
commit is one of **two** required causes, invisible until the production change
reaches it, and that blame's route back to it runs through a rename.

## Commit structure

```text
c0  Add the late fee and its test         cents = daysLate * 50; the test expects 150 for three days
c1  Expect the fee to skip the first overdue day   the test expects 100          <- BIC
c2  Rename the test helper to say what it compares  expect -> assertCents, rewriting the line (distractor)
c3  Charge from the second overdue day, as the test expects   (daysLate - 1) * 50   <- BIC
c4  Charge every overdue day again and expect the full fee                          <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. `c1` alone changes no product behaviour; `c3` alone would
not have been written, and its message says so.

## Measured behaviour

`cents(1)`, `cents(3)` and `cents(10)`, and the value the test expects for three
days, at each commit (`tests/test_deepened_categories.py`):

| commit | cents(1) | cents(3) | cents(10) | the test expects |
|---|---|---|---|---|
| `c0` | 50 | 150 | 500 | 150 |
| `c1` | 50 | 150 | 500 | **100** |
| `c2` | 50 | 150 | 500 | **100** |
| `c3` | **0** | **100** | **450** | 100 |
| `c4` | 50 | 150 | 500 | 150 |

`c1` moves no product answer at all — it only writes down a wrong expectation —
and `c2` renames a helper without touching what the test expects. The fault becomes observable at `c3`, where the
product is changed to agree with the test.

## Measured blame outcome at BFC^

The fix deletes one line in each file:

```text
LateFee.java      "return (daysLate - 1) * CENTS_PER_DAY;"   plain -> c3   -w -> c3   -w -C -C -> c3
LateFeeTest.java  "assertCents(fee.cents(3), 100);"         plain -> c2   -w -> c2   -w -C -C -> c2
```

Blame returns `{c2, c3}`: the product change, which is right, and the rename,
which changed no expectation. `c1` is one step back along the test line's
history, and no blame variant crosses the rename, because it changed the line's
tokens rather than its whitespace.

## What a tool must do to pass

Report exactly `{c1, c3}`. Two things are needed, and a tool that looks only at
product code does neither: follow the test line past the rename to the
commit that wrote the expectation, and treat a test-only change as capable of
introducing a fault at all.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

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
commit is one of **two** required causes, that it makes no product answer wrong
— only the suite red — and that blame's route back to it runs through a
rename.

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

Both are necessary, and their effects are **disjoint**: `c1` owns the
expectation, `c3` owns the fee, and the fix restores exactly their union. `c1`
alone changes no product behaviour; `c3` alone would not have been written, and
its message says so.

## Measured behaviour

`cents(1)`, `cents(3)`, `cents(10)` and `cents(42 949 672)` — the top of the
supported domain — the value the test expects for three days, and the verdict
of `example.LateFeeTest` itself, at each commit
(`tests/test_deepened_categories.py`):

| commit | cents(1) | cents(3) | cents(10) | cents(42 949 672) | the test expects | `LateFeeTest` |
|---|---|---|---|---|---|---|
| `c0` | 50 | 150 | 500 | 2147483600 | 150 | passes |
| `c1` | 50 | 150 | 500 | 2147483600 | **100** | **fails** |
| `c2` | 50 | 150 | 500 | 2147483600 | **100** | **fails** |
| `c3` | **0** | **100** | **450** | **2147483550** | 100 | passes |
| `c4` | 50 | 150 | 500 | 2147483600 | 150 | passes |

`c1` moves no product answer at all — it only writes down a wrong expectation —
and `c2` renames a helper without touching what the test expects. **The fault is
not latent, and the scenario does not claim it is**: what `c1` moves is the
suite's verdict. `LateFeeTest` is red from `c1` until `c3` turns it green again
by changing the product to agree with it. The *product* fault becomes observable
at `c3`; the inconsistency is observable from `c1` onwards, as a failing test.

That red window is the trail a tool can follow: the commit that made the test
pass again is not the commit that made it wrong. (An earlier revision of this
README claimed the fault became observable only at `c3`, which running
`LateFeeTest` at each commit refutes — found in the review of PR #86.)

## Supported domain

`cents` takes its product in `int`, so the domain is `0 <= daysLate <=
42 949 672`, the largest number of overdue days whose fee still fits; the
Javadoc on the method says so and `tests/test_reference_arithmetic.py` holds
the boundary. One day further wraps the correct form to −2 147 483 646. The
faulty form charges a day less and so wraps a day later, which is why the bound
belongs to the fix rather than to the fault, and why the scenario states it
instead of widening: the fault is the missing day, not the width.

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
introducing a fault at all. A tool that runs the suite has a second route to the
same commit — the test has been failing since `c1` — and the one thing it must
not conclude is that `c3`, which made the suite green, is the whole answer.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

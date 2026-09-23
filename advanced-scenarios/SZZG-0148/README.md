# SZZG-0148: Partial credit whose threshold blame cannot meet: three causes, one reachable

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `partial-credit`, `addition-only-fix`, `null-check-omission`, `missing-branch`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `partial_credit`; required `c1`, `c3`, `c4`; minimum 2 · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
| graph features | 3 BICs; 3 fault sites; policy `partial_credit` |
<!-- /szzbench:header -->

## Purpose

A second discriminating mechanism for the suite (issue #80). The thirty-two
scenarios that preceded this one and SZZ-0218 are all two-commit oracles under
`exact_set` whose failure is one unreachable half. Here the oracle names **three** commits and the pass
condition is a **threshold**: `partial_credit` with `minimum_required: 2`. Only
one of the three repairs deletes a line, so blame returns one true positive and
no false positive, and fails by being short rather than by being wrong.

It is the discriminating twin of [SZZG-0138](../SZZG-0138/README.md), which has
the same policy and threshold and *passes*, because two of its three causes sit
on lines the fix deletes. The pair isolates the threshold itself: same shape,
same policy, one reachable cause fewer.

## Commit structure

```text
c0  Add the payslip net calculation                         grossCents * taxPercent / 100, in 64 bits
c1  Take the tax off the gross in percent steps             grossCents / 100 * taxPercent  (truncates)   <- BIC
c2  Write down what a payslip contains                      docs only
c3  Add the declared allowance to the payslip               allowanceCents() dereferences a nullable      <- BIC
c4  Add the employer contribution per contract kind          switch with no CONTRACTOR case               <- BIC
c5  Take the tax off the whole gross, accept an absent declaration and pay the contractor rate            <- BFC
```

## Expected BIC / BFC

- BICs: `c1`, `c3` and `c4` (`partial_credit`, `required: [c1, c3, c4]`,
  `minimum_required: 2`)
- BFC: `c5`

Any two of the three pass; one does not. A false positive still fails, as it
does under every policy.

## Measured behaviour

`netCents(19999, 20)`, `netCents(999999999, 33)`, `allowanceCents(50)`,
`allowanceCents(null)`, `contributionCents("PERMANENT", 100000)` and
`contributionCents("CONTRACTOR", 100000)` at each commit
(`tests/test_second_mechanism.py`; `allowanceCents` exists from `c3`,
`contributionCents` from `c4`):

| commit | net(19999, 20) | net(999999999, 33) | allowance(50) | allowance(null) | permanent | contractor |
|---|---|---|---|---|---|---|
| `c0` | 16000 | 670000000 | — | — | — | — |
| `c1`, `c2` | **16019** | **670000032** | — | — | — | — |
| `c3` | 16019 | **670000032** | 5000 | **NullPointerException** | — | — |
| `c4` | 16019 | **670000032** | 5000 | **NullPointerException** | 10000 | **0** |
| `c5` | 16000 | 670000000 | 5000 | 0 | 10000 | 6666 |

Twenty percent of 19999 cents is 3999 after truncation; `c1` divides first,
`19999 / 100 = 199`, and takes 3980. The second probe is there because
`999999999 * 33` leaves the `int` range: both expressions take the product in
64 bits, so the *only* difference between them is the order of the division and
the multiplication, at any gross and any percentage. Written as a plain `int`
product the correct expression would answer 67949672 for a gross of 50000000 at
50% — more than the gross — and the faulty one would be the accurate of the
two. The three causes are independent: each moves answers the others do not
touch, and the fix repairs all three.

## Measured blame outcome at BFC^

The fix's diff is **one deletion and six additions**. The single deleted line
is `c1`'s:

```text
"return grossCents - (int) ((long) grossCents / 100 * taxPercent);"   plain -> c1   -w -> c1   -w -C -C -> c1
```

The repair of `c3`'s omission adds a null guard above the dereference, and the
repair of `c4`'s omission adds a `case` to the switch; neither deletes
anything. So blame answers `{c1}`: **one** of three required commits, with no
false positive. `minimum_required` is 2, so it fails the threshold.

## What a tool must do to pass

Report at least two of `{c1, c3, c4}` and nothing else. One of them is on a
deleted line; the other two have to be reached from what the fix *adds* — a
guard, back to the commit that wrote the dereference it protects, and a
`case`, back to the commit that wrote the switch without it. A report should
also state the credit ratio and the threshold it was scored against, because
under this policy "found one of three" and "found two of three" are different
results with the same shape.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. Every position rule names one commit, which is below the
threshold; `position-all-non-fix` and every author rule add a commit outside
the required set. It is declared `tier: discriminating` and `szzbench
baselines` confirms the declaration.

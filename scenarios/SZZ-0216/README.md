# SZZ-0216: A method moved to a new class between two faults carries the first one's line into a file blame reads as new

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S5` Refactoring, move, and rename after BIC |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `multi-file-bfc`, `method-move`, `refactoring-after-bic`, `candidate-selection-distractor`, `boundary-condition`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S5 (issue #35). S5's controls move,
rename or extract code after a single BIC and ask whether the tool follows the
code ([SZZ-0128](../SZZ-0128/README.md) extracts a helper, [SZZ-0125](../SZZ-0125/README.md)
renames a method); the second-commit rule solves every one of them. Here the
move sits between two independent faults that one fix repairs in two files.
Blame in the new file stops at the commit that created it under every default
setting; the first fault is reached only by treating the new file as a copy of
the old one.

## Commit structure

```text
c0  Add the ticket pricing                       TicketPricing: basePriceCents (age < 12), groupPriceCents (base * count)
c1  Tidy the child fare condition                age <= 12                                        <- BIC
c2  Move the fare table into its own class       FareTable.java created with the fare lines, token for token; TicketPricing delegates
c3  Rework the group price arithmetic            base + count                                     <- BIC
c4  Charge the adult fare from age twelve and multiply the group price by the head count   two files   <- BFC
```

Git's own copy detection sees `c2` as `{TicketPricing.java => FareTable.java}`
(`git show --stat -C --find-copies-harder`), which is why `git log --follow` on
the new file continues into the old one.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

`c2` is not a BIC: it changes no token of the fare check and no behaviour.

## Measured behaviour

`basePriceCents(age)` for ages 11, 12 and 13 and `groupPriceCents(30, 3)` at
each commit (`tests/test_rebalance_scenarios.py`):

| commit | base 11 | base 12 | base 13 | group 30 × 3 |
|---|---|---|---|---|
| `c0` | 500 | 1200 | 1200 | 3600 |
| `c1` | 500 | **500** | 1200 | 3600 |
| `c2` | 500 | 500 | 1200 | 3600 |
| `c3` | 500 | 500 | 1200 | **1203** |
| `c4` | 500 | 1200 | 1200 | 3600 |

`c1` gives twelve-year-olds the child fare; `c2` changes nothing; `c3` adds the
head count to one fare instead of multiplying. The two faults are independent,
and the partial fix measured at `c3` shows both are necessary: restoring `<`
alone leaves the group price at 1203; restoring `*` alone leaves a
twelve-year-old at 500.

## Measured blame outcome at BFC^

The fix deletes one line in each file:

```text
FareTable.java     "return age <= 12 ? CHILD_CENTS : ADULT_CENTS;"   plain -> c2   -w -> c2   -M -> c2   -C -> c2   -C -C -> c2   -C10 -> c1
TicketPricing.java "return basePriceCents(age) + count;"             plain -> c3   -w -> c3   -C -C -> c3
```

Blame returns `{c2, c3}`: it misses `c1` and names the move. The fare line was
copied into a new file with the class header and two constants around it, a
chunk below Git's default copy score, so `-C`, `-C -C` and `-M` stop at `c2`;
only a lowered score (`-C10`) follows the copy to `c1`. `git log --follow`
on `FareTable.java` lists `c2`, `c1`, `c0`.

## What a tool must do to pass

Report exactly `{c1, c3}`. `c2` must be rejected as behaviour-preserving, and
`c1` reached across the move: by lowering blame's copy score, by following the
new file's history as a copy of the old one, or by matching the moved
expression in the file it came from.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

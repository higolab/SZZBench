# SZZG-0151: A merge takes the branch's side and puts the reverted unit back without saying so

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `revert`, `reintroduction`, `merge`, `value-flow`, `blame-unreachable-bic` |
| oracle | default: `reintroduction_direct`; required `c4`, `c5`; related origins `c1`; related but not correct `c2` · `origin-aware`: `exact_set`; required `c4`, `c5`; related origins `c1`; related but not correct `c2` · BFC `c6` |
| defeats | `blame`, `shape`, `position` |
| graph features | 2 branches; merge commit `c4`; revert `c2`; 3 BICs; 2 fault sites; policy `reintroduction_direct`; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

G6's second `discriminating` scenario, after
[SZZG-0147](../SZZG-0147/README.md). Both are reintroductions, and in both the
answer is the commit that put the change back in force rather than the commit
that first made it. SZZG-0147 reintroduces by a **revert of a revert**, which
leaves a commit whose message says what it did. Here the reintroduction is a
**merge resolution**: a branch forked before the revert still carried the euro
form, the merge resolved the conflict in its favour, and nothing in the history
says the change came back.

## Commit structure

```text
c0  main       Add the daily rate card               DAILY_CENTS = 500; totalCents = days * DAILY_CENTS
c1  main       Express the daily rate in euros       DAILY = 5; totalCents = days * DAILY * 100    (origin)
c2  main       Revert "Express the daily rate in euros"   real git revert of c1                    (related, not correct)
c3  reporting  Show the daily rate on the quote      dailyLabel() = DAILY + " EUR"   (forked at c1)
c4  main       Merge the reporting branch            resolution takes the branch's file: euros again   <- BIC
c5  main       Add the express surcharge to the daily rate   expressCents() = DAILY + 50               <- BIC
c6  main       Charge the express surcharge on a rate in euros   DAILY * 100 + 50                      <- BFC
```

`c2` is a real `git revert` with the message Git writes. The `reporting` branch
forks at `c1`, so it never saw the revert; the merge `c4` conflicts, because
main's revert and the branch both rewrote the region around the constant, and
the resolution keeps the branch's version.

## Expected BIC / BFC

- BICs: `c4` and `c5` (`reintroduction_direct`, `required: [c4, c5]`)
- `c1` is the origin (`related_origins`), tolerated under the `origin-aware`
  variant and a false positive under the default; `c2` is
  `related_but_not_correct`
- BFC: `c6`

Both are necessary. Without `c5` nothing reads `DAILY` as cents; without `c4`
the revert stands and the constant is 500. The direct/origin contract
attributes a reintroduced change to the commit that reintroduced it, which here
is a merge.

## Measured behaviour (from the generated repository)

`totalCents` at one day, seven days and the top of the supported domain, the
label, and the surcharge, at each commit
(`tests/test_graph_deepened_categories.py`):

| commit | `totalCents(1)` | `totalCents(7)` | `totalCents(4 294 967)` | `dailyLabel` | `expressCents` |
|---|---|---|---|---|---|
| `c0` | 500 | 3500 | 2147483500 | — | — |
| `c1` | 500 | 3500 | 2147483500 | — | — |
| `c2` | 500 | 3500 | 2147483500 | — | — |
| `c3` | 500 | 3500 | 2147483500 | "5 EUR" | — |
| `c4` | 500 | 3500 | 2147483500 | "5 EUR" | — |
| `c5` | 500 | 3500 | 2147483500 | "5 EUR" | **55** |
| `c6` | 500 | 3500 | 2147483500 | "5 EUR" | 550 |

The rate is five euros a day throughout, and every commit up to `c4` agrees on
every probe: `c1` converts the constant and its only reader together, `c2`
converts them back, and the merge converts them forward again. The label is
right when it appears. Only the surcharge is wrong, from `c5` until `c6`.

## Measured blame outcome at BFC^

```text
"return DAILY + 50;"          plain -> c5   -w -> c5   -w -C -C -> c5
"static final int DAILY = 5;" plain -> c1   -w -> c1   -w -C -C -> c1
"return days * DAILY * 100;"  plain -> c1   -w -> c1   -w -C -C -> c1
```

Blame returns `{c5}`. Following the constant leads to `c1` — the commit whose
change was **reverted**, which the direct/origin contract does not accept as
the answer — and `c4`, the merge that put it back, is on no line of the file.
`git log --first-parent` gives `c6, c5, c4, c2, c1, c0`: the required merge is
on that path, and so is the origin that must not be reported.

## What a tool must do to pass

Report exactly `{c4, c5}`. This is the unusual shape in the tier: the trouble
is not that the second commit is out of reach but that the reachable one is
**wrong**. A tool has to notice that `c1`'s change was undone, that the file
carries it again after a merge, and that the commit which performed that merge
is the one responsible — although its message says only that a branch was
merged and its diff against its first parent is not a diff anyone wrote.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.

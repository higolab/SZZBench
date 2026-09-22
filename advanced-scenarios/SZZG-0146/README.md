# SZZG-0146: One history, two contracts: the default variant requires the cause, the other only the commit that made it visible

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `evaluation-variant`, `caller-callee`, `value-flow`, `wrong-constant`, `blame-unreachable-bic` |
| oracle | default (`full-cause`): `exact_set`; required `c1`, `c3` · `observable-only`: `relaxed_with_related`; required `c3`; related origins `c1` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
| graph features | 2 BICs; 2 fault sites; 2 evaluation variants (`full-cause`, `observable-only`) |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in G9 (issue #35). The history is the
*callee* kind of the measured axis — a callee changes what it returns and its
only caller is converted with it, then a new caller assumes the old contract,
as in [SZZ-0191](../../scenarios/SZZ-0191/README.md). G9's contribution is the
**pair of evaluation variants** on top of it: `full-cause` requires both
commits and is the default; `observable-only` requires only the commit that
made the fault visible and tolerates the callee change as a related origin.
Plain blame fails the first and passes the second. The scenario exists so that
a pass under the lenient contract cannot be reported as a pass on the tier.

## Commit structure

```text
c0  Add the percentage parser and the discount   parse("15%") = 15; apply() divides by 100
c1  Parse percentages to basis points            parse("15%") = 1500; apply() divides by 10000   <- BIC
c2  Describe the discount rules                  docs only (distractor)
c3  Describe a discount on the receipt           describe() = parse(percent) + " percent off"   <- BIC
c4  Describe the discount as a percentage on the receipt   parse(percent) / 100                 <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` under the default variant `full-cause` (`exact_set`,
  `required: [c1, c3]`)
- BFC: `c4`
- Variant `observable-only`: `relaxed_with_related`, `required: [c3]`,
  `related_origins: [c1]` — `{c3}` and `{c1, c3}` both pass; `{c1}` alone and
  anything with another commit fail.

Both commits are necessary under the default. Without `c3` nothing prints the
parser's result; without `c1` the parser returns whole percent and `c3`'s
receipt is right.

## Measured behaviour

`apply(2000, "15%")`, `describe("15%")` and `describe("7%")` at each commit
(`tests/test_rebalance_scenarios.py`; `Receipt` exists from `c3`):

| commit | apply(2000, "15%") | describe("15%") | describe("7%") |
|---|---|---|---|
| `c0`–`c2` | 1700 | — | — |
| `c3` | 1700 | **1500 percent off** | **700 percent off** |
| `c4` | 1700 | 15 percent off | 7 percent off |

`c1` changes no answer: the parser and its only caller change together.
**Counterfactual, measured:** undoing `c1` on top of `c3` — `parse()` returning
whole percent, `apply()` dividing by 100 — gives `15 percent off` and
`7 percent off`, the fixed answers.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return Percent.parse(percent) + \" percent off\";"    plain -> c3    -w -> c3    -w -C -C -> c3
```

Blame returns `{c3}`. Scored under `full-cause`, that is a false negative on
`c1` and a **FAIL**; scored under `observable-only`, it is a **PASS**. The
evaluator reports the variant it used, and `szzbench baselines` scores the
default.

## What a tool must do to pass

Report exactly `{c1, c3}` under the default variant: follow `Percent.parse()`
from the fixed expression to the commit that changed its scale. A result on
this scenario has to name the variant it was scored under; a pass under
`observable-only` is a pass on a different question.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario under the default
variant — metadata, position, shape or blame. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.

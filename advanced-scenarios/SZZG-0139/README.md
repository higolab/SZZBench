# SZZG-0139: Partial credit across a merge: one BIC on each side, either one is a passing answer

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `partial-credit`, `multi-bic`, `single-bfc`, `branch-merge` |
| oracle | `partial_credit`; required `m1`, `f1`; minimum 1; known distractors `c2` · BFC `c3` |
| graph features | 2 branches; merge commit `c2`; 2 BICs; 2 fault sites; policy `partial_credit` |
<!-- /szzbench:header -->

## Purpose

Third member of the `partial_credit` family ([SZZG-0033](../SZZG-0033/README.md),
[SZZG-0138](../SZZG-0138/README.md)). A booking total is too low for two
independent reasons: on the main line the nightly base price loses a night
(`(nights - 1) * 10000`), and on a feature branch the weekend surcharge becomes a
discount (`price - price / 10`). The branch is merged and one commit fixes both.
With `minimum_required: 1`, a tool that walks only the first-parent line and
finds `m1` passes with `f1` as a false negative; a tool that blames the merge
commit fails. The policy separates "found one side of the merge" from "blamed the
merge".

## Commit structure (generated)

```text
* dfc6580  2024-04-22  Restore the nightly base price and the weekend surcharge  <- BFC (c3)
*   5f9b23d  2024-04-15  Merge branch feature: weekend surcharge rounding        (c2, merge; known distractor)
|\
| * 0058ac1  2024-04-08  Round the weekend surcharge the way the invoice does    <- BIC (f1, feature)
* | 95546e6  2024-04-10  Do not charge the check-out day                         <- BIC (m1, main)
|/
* 4742259  2024-04-01  Add the booking price components                          (c0)
```

## Expected BIC / BFC

- `partial_credit`, `required: [m1, f1]`, `minimum_required: 1`, `known_distractors: [c2]`
- BFC: `c3`

## Measured behaviour and blame

| commit | `basePrice(3)` | `weekend(10000)` |
|---|---|---|
| `c0` | 30000 | 11000 |
| `m1` | **20000** | 11000 |
| `f1` | 30000 | **9000** |
| `c2` | 20000 | 9000 |
| `c3` | 30000 | 11000 |

`c3` is the only commit whose first-parent diff touches both files. Blame at
`c3^` (the merge) returns `m1` for `Pricing.java` line 6 and `f1` for
`Surcharge.java` line 6. `git rev-list --first-parent c3` is `c3, c2, m1, c0`: a
first-parent walk never sees `f1`.

## What the evaluator says (`tests/test_policy_families.py`)

| answer | status |
|---|---|
| `{m1, f1}`, `{m1}`, `{f1}` | PASS (`{m1}` and `{f1}` with one false negative and credit 1/2) |
| `{c2}`, `{m1, c2}` | FAIL — the merge introduced nothing |
| `{}` | FAIL |

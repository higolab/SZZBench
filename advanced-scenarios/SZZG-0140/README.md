# SZZG-0140: Top-k with a strict status cut-off: the BIC must be ranked first, hit@3 is only reported

## Purpose

Third member of the `top_k` family ([SZZG-0096](../SZZG-0096/README.md): ranking
inside a work item; [SZZG-0115](../SZZG-0115/README.md): `k_values: [1, 3, 5]`).
This scenario has SZZG-0115's `k_values` and adds `status_k: 1`, so `hit@1`,
`hit@3` and `hit@5` are all reported but only `hit@1` decides PASS/FAIL. The
history makes the difference bite: the faulty line is reformatted after the BIC,
so a tool that ranks candidates by blame recency puts the reformatting commit
first and the BIC second — `hit@3` but not `hit@1`.

## Commit structure (generated)

```text
* 1eacd10  2024-07-01  Allow the limit itself again                 <- BFC (c4)
* bc87e35  2024-06-24  Add the alert message                        (c3, unrelated)
* 7e2753c  2024-06-17  Reformat Threshold to the project style      (c2, rewrites the faulty line; known distractor)
* f9287a2  2024-06-10  Alert when the limit is reached              <- BIC (c1)
* 517739c  2024-06-03  Add the threshold check                      (c0)
```

## Expected BIC / BFC

- `top_k`, `relevant: [c1]`, `k_values: [1, 3, 5]`, `status_k: 1`
- `related_but_not_correct` and `known_distractors`: `c2`
- BFC: `c4`

## Measured behaviour and blame

`exceeds(10, 10)` is `false` at `c0`, **`true`** at `c1`, `c2`, `c3`, and `false`
at `c4`. `c2` rewrote `return value >= limit;` into
`boolean exceeded = value >= limit; return exceeded;`, so the declared fault
statement is not present at `c4^` (verifier `GI701`, declared by
`formatting-noise`); blaming the line `c4` deletes (line 6) returns `c2`.

## What the evaluator says (`tests/test_policy_families.py`)

| ranked answer | `hit_at` | status here (`status_k: 1`) | status in SZZG-0115 (no `status_k`) |
|---|---|---|---|
| `c1` first | `{1: true, 3: true, 5: true}` | PASS | PASS |
| `c2` first, `c1` second | `{1: false, 3: true, 5: true}` | **FAIL** | PASS |

False positives never fail a `top_k` scenario; the rank of the first relevant
commit does.

## Factors

- `top-k`
- `formatting-noise`
- `basic-blame-distractor`
- `boundary-condition`
- `single-bic`
- `single-bfc`

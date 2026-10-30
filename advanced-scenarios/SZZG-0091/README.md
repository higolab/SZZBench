# SZZG-0091: Multiple BICs with partial revert reintroducing one fault

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `revert`, `partial-revert`, `multi-bic`, `single-fault-reintroduced`, `origin-vs-direct`, `wrong-operator` |
| oracle | default: `exact_set`; required `c4`; related origins `c2`; related but not correct `c1`, `c3` · `origin-aware`: `relaxed_with_related`; required `c4`; acceptable `c2` (credit 0.5); related but not correct `c1`, `c3` · BFC `c5` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 BICs; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Two original BICs in `InvoiceSummary.summarize`: `c1` swaps the `PAID`/`OPEN`
labels, `c2` adds the credit to the amount due instead of subtracting it. `c3`
fixes both. `c4` partially reverts `c3` and adds the credit again; `c5` fixes
that. For the final fix the direct BIC is the partial revert `c4`; `c2` is the
origin of the reintroduced fault; `c1` and `c3` are related history a tool must
not report.

Rewritten 2026-09-21 (issue #13) from the shared `aboveMin`/`belowMax` template;
the history shape, oracle, variants and coverage dimensions (`bic_depth` 1, four
distractors on the fault file, 6 commits, 1 ref) are unchanged — including the
origin mapping: as in the template version, the fault `c4` reintroduces is the
one `c2` wrote (PR #63 review).

## Commit structure (generated)

```text
* ce29e78  2025-04-07  Subtract the credit from the amount due again                    <- BFC (c5)
* 8a92d96  2025-04-04  Revert the balance change                                        <- BIC (c4; partial revert of c3)
* 0e5a430  2025-04-02  Subtract the credit and put the status labels the right way round (c3, prior fix)
* 132a5c9  2025-03-31  Apply the credit to the amount due                               <- origin (c2)
* d054567  2025-03-25  Rename the status labels                                         (c1, first origin fault; never reintroduced)
* 0e66a70  2025-03-24  Add the invoice summary                                          (c0)
```

## Expected BIC / BFC

- default: `required: [c4]`, `related_but_not_correct: [c1, c3]`, `related_origins: [c2]`
- `origin-aware`: `relaxed_with_related`, `c2` at 0.5
- BFC: `c5`

## Measured behaviour and blame

`summarize(100, 30, false)`:

| commit | result |
|---|---|
| `c0` | `OPEN 70` |
| `c1` | **`PAID 70`** (labels swapped) |
| `c2` | **`PAID 130`** (both faults) |
| `c3` | `OPEN 70` |
| `c4` | **`OPEN 130`** |
| `c5` | `OPEN 70` |

`c5` deletes one line (`int due = amount + credit;`, line 5); blame at `c5^`
returns `c4` (verifier `GI703`).

Under the `origin-aware` variant `{c4, c2}` passes and `{c4, c1}` fails, exactly
as before the rewrite; `tests/test_template_rewrites.py` asserts both verdicts
and compares the scoring-relevant oracle of every rewritten scenario with its
pre-rewrite version.

## What a tool must do

Report `c4` alone. Reporting the original BIC set `{c1, c2}` — the answer to the
prior fix `c3` — is wrong for the final fix: `c1`'s fault never came back, and
`c2`'s came back through `c4`.

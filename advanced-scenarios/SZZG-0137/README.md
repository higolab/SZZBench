# SZZG-0137: The fault is present since the initial commit, which wrote it: c0 is the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `initial-commit-bic`, `single-bic`, `single-bfc`, `tool-visible-context` |
| oracle | `exact_set`; required `c0` · BFC `c3` |
| graph features | `issues` |
<!-- /szzbench:header -->

## Purpose

The third contract for "the fix's deleted line belongs to the first commit"
(issue #24) — the one where there is an ordinary BIC after all. This is the twin
of [SZZG-0136](../SZZG-0136/README.md): the same `LateFee.java`, the same later
commits, the same report and the same fix, but `c0` says "Add the late-fee
calculation" and nothing points to an earlier history. An authored first commit
that wrote the fault is its bug-introducing commit like any other, the contract
SZZ-0180 already applies to its large initial import.

## Commit structure (generated, every author and date pinned)

```text
* 911e501  2024-01-29  Charge only the days beyond the grace period                  <- BFC (c3)
* 471efdd  2024-01-22  Record the report about late fees charged from the first day   (c2, writes docs/issues/ISSUE-8.md)
* feb4f6c  2024-01-15  Add the invoice reminder text                                 (c1, unrelated)
* ca29dad  2024-01-08  Add the late-fee calculation                                  <- BIC (c0)
```

## Expected BIC / BFC

- BIC: `c0` (`exact_set`, `required: [c0]`)
- BFC: `c3`

## Measured behaviour and blame

`feeCents(5, 3, 100)` is **500** at `c0`, `c1`, `c2` and **200** at `c3`. Blaming
line 13 of `LateFee.java` at `c3^` returns `c0`, the expected BIC (verifier:
`GI703`). `c1`–`c3` are byte-identical to SZZG-0136's in message, author, date and
source tree; only `c0`'s message differs and `docs/IMPORT.md` is absent
(`tests/test_policy_families.py`).

## What a tool must do

Report `c0`, and do not abstain merely because the answer is the root commit.
Read next to SZZG-0136: the same blame result is right here and wrong there, and
only the provenance evidence in the repository tells the two apart.

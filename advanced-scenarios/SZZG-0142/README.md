# SZZG-0142: An origin worth a full point: credit 1.0 fills the metric while the status still needs the direct BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `relaxed-credit`, `origin-vs-direct`, `copy-propagation`, `wrong-constant`, `single-bic`, `single-bfc`, `evaluation-variant` |
| oracle | default (`direct-only`): `exact_set`; required `c2`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · `relaxed-with-credit`: `relaxed_with_credit`; required `c2`; acceptable `c1` (credit 1) · BFC `c3` |
| graph features | 2 BICs; origin faults; 3 evaluation variants (`direct-only`, `origin-aware`, `relaxed-with-credit`); `copy_relationships` |
<!-- /szzbench:header -->

## Purpose

Third member of the `relaxed_with_credit` family ([SZZG-0022](../SZZG-0022/README.md),
[SZZG-0141](../SZZG-0141/README.md)), with the largest credit value. A shared
timeout constant is lowered from 3000 to 30 milliseconds (`c1`, the origin) and
the HTTP client configuration inlines the wrong value (`c2`, the direct BIC); the
fix corrects the copy. In the `relaxed-with-credit` variant the origin is worth a
full point: an answer of `{c1}` alone reaches `credit_ratio` 1.0 and still
fails, because the status is decided by the required set. The `origin-aware`
variant keeps the suite's 0.5 convention (D3), so the two variants show the same
answer at two credit values.

## Commit structure (generated)

```text
* c147790  2024-10-28  Use a 3 second connect timeout in the HTTP client                       <- BFC (c3)
* 91b42f6  2024-10-21  Add the HTTP client configuration with the connect timeout inlined      <- direct BIC (c2)
* 12a1c3a  2024-10-14  Lower the connect timeout to 30                                         <- origin (c1)
* fbf40c9  2024-10-07  Add the shared timeout constants                                        (c0)
```

## Expected BIC / BFC

- default (`direct-only`): `required: [c2]`, `related_origins: [c1]`
- `origin-aware`: `relaxed_with_related`, `c1` as `acceptable_related` at 0.5
- `relaxed-with-credit`: `relaxed_with_credit`, `c1` as `acceptable_related` at **1.0**
- BFC: `c3`. `Timeouts.connectMillis()` stays 30; it is the origin and is not fixed here.

## Measured behaviour and blame

`Timeouts.connectMillis()` is 3000 at `c0` and **30** from `c1` on;
`HttpClientConfig.connectTimeoutMillis()` is **30** at `c2` and 3000 at `c3`.
Blaming the line `c3` deletes (`return 30;`, line 6 of `HttpClientConfig.java`)
at `c3^` returns `c2`.

## What the evaluator says (`tests/test_policy_families.py`)

| variant | answer | `weighted_credit` / `possible_credit` | status |
|---|---|---|---|
| default | `{c2}` | 1.0 / 1.0 | PASS |
| default | `{c1}` | — | FAIL (false positive, `c2` missing) |
| `relaxed-with-credit` | `{c1}` | **1.0 / 1.0** | **FAIL** (`c2` missing) |
| `relaxed-with-credit` | `{c2, c1}` | min(1, 1 + 1.0) = 1.0 / 1.0 | PASS |
| `origin-aware` | `{c1}` | 0.5 / 1.0 | FAIL |

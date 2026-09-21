# Evaluation policies

This document specifies how `szzbench evaluate` (implemented in
`src/szzbench/evaluator.py`) turns a scenario's `expected_szz` oracle and a
tool's predictions into a PASS/FAIL status and the accompanying metrics. It is
the reference for scenario authors and for anyone reading the JSON or Markdown
reports. Everything here describes the implemented behaviour; the automated
tests in `tests/test_evaluator_semantics.py` pin the statements down.

Evaluation is **commit-level** only. Oracle sections such as `bug_level`,
`branch_level`, `entity_level`, `line_level`, `bug_instances`, and
`work_item_level` are not scored; when a graph scenario declares them, the
result carries a `result_notes` entry saying so. `Prediction.fix_commit` is
accepted but not matched during scoring.

## 1. Inputs

### 1.1 Predictions

A prediction record names a scenario and one or more inducing commits, each
optionally with a `rank` (integer, 1 = best) and a `confidence`. The value of
`inducing_commit` is normalized against the scenario's `commit-map.json`:

| accepted spelling | example | normalized to |
|---|---|---|
| logical commit id from `commit-map.json` | `c2` | `c2` |
| full Git hash | `9f3b...` (40 hex chars) | the logical id that owns the hash |
| hash prefix of at least 7 characters that matches exactly one commit | `9f3b0a1` | the logical id |
| anything else | `HEAD`, a 6-char prefix, an ambiguous prefix | **unknown prediction** |

Accepting logical ids is a deliberate interface choice: adapters and tests can
write oracle-style ids without regenerating repositories, and a tool running on
the generated repository naturally emits hashes. Both forms are equivalent for
scoring. An unknown prediction makes the scenario **FAIL** under every policy
and is listed in `unknown_predictions`.

Duplicates are collapsed (the first occurrence wins). When at least one
prediction of a scenario carries a `rank`, the predictions are ordered by rank
(unranked ones last, in input order); otherwise input order is the rank order.
This ordered, de-duplicated list is `top_k.ranked_actual_bics`; its set is
`actual_bics`.

### 1.2 Oracle: classic scenarios (`scenarios/*/scenario.yml`)

The classic suite always uses `exact_set`. Per bug, `expected_szz.commit_level`
provides:

| key | meaning |
|---|---|
| `true_positives` | required commits (fallback: the bug's `bug_introducing_commits`) |
| `false_positives_allowed` | treated as `acceptable_related` with credit 0 |
| `known_distractors` | diagnostic bucket, see section 5 |

The sets of all bugs are unioned. Variants are not available in the classic
suite.

### 1.3 Oracle: graph scenarios (`advanced-scenarios/*/scenario.graph.yml`)

`expected_szz.commit_level` is the default oracle. `expected_szz.evaluation_variants`
is an optional list of `{name, description, commit_level}` entries and
`default_variant` names the one used when `--evaluation-variant` is omitted.
Variant names are matched after lower-casing and treating `-` and `_` alike.
A variant's `commit_level` **replaces** the base `commit_level`; only
`evaluation_policy` is inherited when the variant omits it. A variant without a
`commit_level` falls back to the inferred required set (section 1.4) with a
note.

Keys understood inside `commit_level` (base or variant):

| key | type | role |
|---|---|---|
| `evaluation_policy` | string | one of the policies in section 2 (default `exact_set`; unknown names are treated as `exact_set` with a note) |
| `required` | list of ids | the commits a correct answer must contain |
| `acceptable_related` | list of ids or `{commit, reason, credit}` | always protected, optionally credited |
| `related_origins` | list of ids | protected under relaxed evaluation only |
| `related_but_not_correct` | list of ids | never protected; excluded from *hard* false positives |
| `relevant` | list of ids | the hit set for `top_k` (default: `required`) |
| `k_values` | list of positive ints | cut-offs reported in `top_k.hit_at` |
| `status_k` | positive int | the cut-off that decides PASS/FAIL under `top_k` |
| `minimum_required` | non-negative int | threshold for `partial_credit` |
| `expect_no_bic` | boolean | intentionally empty oracle (section 6) |
| `known_distractors` | list of ids | diagnostic bucket (section 5) |

### 1.4 Missing `required`: inference from bug metadata

When `required` is absent or empty and `expect_no_bic` is not set, the
evaluator infers it from `bugs[].bug_introducing_commits`, taking every entry
whose normalized role (section 8) is `direct`, `reintroducing`, or
`contributing`. The result always says so:

```
commit_level.required is missing or empty; required BICs inferred from
bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
```

If nothing can be inferred either, the required set is empty and the note
recommends `expect_no_bic: true`. An empty required set without
`expect_no_bic` is *not* an "expect nothing" oracle: under `exact_set` any
prediction is then a false positive and no prediction passes, which is the
same outcome but without the explicit intent.

Notes like these are not hidden in the JSON: `evaluate` promotes every
oracle-related result note (inferred required set, `expected_szz` sections the
commit-level evaluator does not read, ignored allowances, unsupported policy
names) to a report warning prefixed with the scenario id, which the plain CLI
prints and the Markdown report lists under `## Warnings`; in addition the
Markdown report ends with a `## Scenario notes` section that lists all
`result_notes` per scenario. A PASS for a scenario such as SZZG-0116 is
therefore always accompanied by the caveat that its `entity_level` /
`line_level` oracle was not evaluated.

## 2. Derived sets

With `E` = required, `A` = acceptable_related commits, `P` = predicted
(normalized) commits, `O` = related_origins, `R` = related_but_not_correct,
`D` = known_distractors:

| report field | definition |
|---|---|
| `true_positives` | `P ∩ E` |
| `false_negatives` | `E − P` |
| `false_positives` | `P − E − A` |
| `allowed_false_positives` | `P ∩ A` (with `acceptable_related_hits` carrying reason and credit) |
| `related_origin_hits` | `P ∩ O` |
| `related_but_not_correct_hits` | `P ∩ R` |
| `hard_false_positives` | `P − E − A − O − R` |
| `known_distractor_hits` | `P ∩ D` (diagnostic only) |
| `weighted_credit` | `min(|E|, |TP| + Σ credit of acceptable_related hits)`; `null` when `E` is empty |
| `possible_credit` | `|E|`; `null` when `E` is empty |
| `precision`, `recall` | computed from TP/FP/FN (`null` when the denominator is 0) |

Note that `false_positives` is the strict count: a `related_origins` or
`related_but_not_correct` hit *is* a false positive; only `acceptable_related`
removes a prediction from `false_positives`.

## 3. Policies

The status is decided in this order. Steps 1 and 2 apply to every policy.

1. Any unknown prediction → **FAIL**.
2. `expect_no_bic: true` → **PASS** iff `P` is empty (section 6).
3. Policy-specific rule below.

### 3.1 `exact_set`

**PASS iff** `false_positives` and `false_negatives` are both empty. This is the
policy of the whole classic suite and the default for graph scenarios.

### 3.2 `direct_only` and `reintroduction_direct`

Identical to `exact_set` in comparison. The names document *how the required
set was chosen*: `direct_only` requires the commits that directly introduced
the fault (origins of copied or replayed faults are listed separately, usually
as `related_origins` or `related_but_not_correct`); `reintroduction_direct`
requires the commit that reintroduced a previously fixed fault rather than the
original introduction. They do not change the scoring rule.

### 3.3 `partial_credit` (with `minimum_required`)

**PASS iff** `minimum_required_met` is true **and** `false_positives` is empty.
`minimum_required_met` is `|TP| >= minimum_required`; without
`minimum_required` the threshold is `|required|` (i.e. plain exact recall).
Missing required commits beyond the threshold are still reported as
`false_negatives`, and `weighted_credit` / `credit_ratio` express how much of
the oracle was recovered.

### 3.4 `top_k` (with `k_values`, `relevant`, `status_k`)

The evaluator finds `best_rank`, the 1-based position of the first predicted
commit that is in `relevant` (default: `required`). It reports
`hit_at[k]` = `best_rank <= k` for every k in `k_values` (default `[1, 3, 5]`
when `k_values` is absent) and `mrr` = `1 / best_rank` (0 when there is no
hit).

**PASS iff** `best_rank` exists **and** `best_rank <= status_k`, where

- `status_k` is the value declared in `commit_level`, otherwise
- the largest value in `k_values`, otherwise
- `1` when `k_values` is absent.

`status_k` is reported inside `top_k`. False positives never fail a `top_k`
scenario; they are reported as usual. Use `status_k` when the scenario should
be strict about the top rank while still reporting `hit_at` for larger k.

### 3.5 `relaxed_with_related` and `relaxed_with_credit`

**PASS iff** `hard_false_positives` and `related_but_not_correct_hits` are both
empty **and** `false_negatives` is empty. In other words, predicting a
`related_origins` commit is tolerated, predicting a `related_but_not_correct`
commit is not, and every required commit must still be found.
`relaxed_with_credit` is scored exactly like `relaxed_with_related`; the
difference is that its scenarios attach `credit` values to
`acceptable_related`, which show up in `weighted_credit`.

## 4. The three "related" lists

| list | `false_positives` | `hard_false_positives` | affects status under `exact_set` / `direct_only` / `reintroduction_direct` / `partial_credit` | affects status under relaxed evaluation | credit |
|---|---|---|---|---|---|
| `acceptable_related` | excluded | excluded | protects (never a failing FP) | protects | `credit` counts towards `weighted_credit` |
| `related_origins` | counted | excluded | does **not** protect: the prediction fails the scenario | protects | none |
| `related_but_not_correct` | counted | excluded | does not protect | does **not** protect | none |

"Relaxed evaluation" means the policy is `relaxed_with_related` or
`relaxed_with_credit`, **or** the selected variant's name contains `origin` or
`related` (after lower-casing, `-` and `_` treated alike). This variant-name
convention is what makes `origin-aware` / `origin_aware` variants tolerate
`related_origins` even when their `evaluation_policy` is `direct_only` or
`exact_set` (SZZG-0020 is the reference case). Name variants accordingly:
`direct-only`, `direct_bic_only` → strict; `origin-aware`, `related-tolerant`
→ relaxed.

`related_but_not_correct` therefore only changes diagnostics: those hits are
kept out of `hard_false_positives` so a report can separate "found a related
commit" from "found something unrelated", but the scenario still fails.

## 5. `known_distractors` (diagnostic)

`known_distractors` lists commits the scenario deliberately plants to mislead a
tool (a refactoring of the buggy line, a formatting commit, a merge, ...).
Predicting one of them is already a false positive under every policy, so the
list never changes PASS/FAIL. The evaluator reports `known_distractor_hits`
(`P ∩ D`) per scenario, a total in the summary (`known_distractor_hits`), a
`- Known distractor hits:` line, and a `Distractor hits` column in the Markdown
table. This lets a report distinguish "fell for the planted distractor" from
other false positives. Classic scenarios declare it under
`bugs[].expected_szz.commit_level.known_distractors`; graph scenarios may
declare it in any `commit_level`.

## 6. `expect_no_bic`

`expect_no_bic: true` in a `commit_level` (base or variant) declares an
intentionally empty oracle, for example an externally caused fault with no
inducing commit in the repository. The required set is left empty (no
inference), the JSON result carries `"expect_no_bic": true`, and the Markdown
table shows `none (expect_no_bic)` as the expected set.

**PASS iff** the tool makes no prediction for the scenario. Every known
prediction is a false positive and fails; unknown predictions fail as under any
policy. If a scenario sets `expect_no_bic: true` *and* a non-empty `required`,
the flag is ignored with a note (the two are contradictory; `required` wins).

Because every known prediction is a false positive, allowances make no sense
under this policy: when `expect_no_bic` is effective, `acceptable_related`,
`related_origins`, `related_but_not_correct` and `relevant` are ignored (a
note names the ignored lists) so that `false_positives` and
`hard_false_positives` contain every prediction and agree with the FAIL status.

Such a scenario keeps its bug entry and its bug-fixing commit but declares
`bug_introducing_commits: []`. The graph validator accepts the empty list when
`expected_szz.commit_level` (or any evaluation variant) declares
`expect_no_bic: true` — it reports the informational `GI086` instead of the
error `GE084` — so the normal workflow `validate-graph → generate-graph →
evaluate` works. Without the declaration an empty BIC list is still `GE084`.

## 7. Fix shapes

When `evaluate` can see the generated repository
(`<generated-root>/<scenario>/<variant>/repo`), it classifies every
bug-fixing commit declared in `bugs[]` (`bug_fixing_commit` or
`bug_fixing_commits`) by its **first-parent diff**,
`git diff --unified=0 --no-renames <first parent> <bfc>` (a root commit is
diffed against the empty tree):

| class | definition | typical cause | consequence for blame-based SZZ |
|---|---|---|---|
| `empty_first_parent` | the diff is empty | a merge BFC whose first parent already contains the fix (e.g. SZZG-0042) | nothing to blame on the first-parent side |
| `addition_only` | the diff has no deleted lines | the fix adds a guard, a new file, or a missing statement | nothing to blame; a pure "FN" is expected from line-deletion SZZ |
| `modifies` | at least one deleted line | the usual line modification or deletion | blame is applicable |

The result carries `fix_shape` as a map `{bfc id: class}` (or `null` when
nothing could be classified), the summary counts BFCs per class in
`fix_shape_counts`, and the Markdown report has a `- Fix shapes (per BFC):`
line and a `Fix shape` column. When the repository is missing or Git fails,
the classification is skipped and the reason is added to `result_notes`. Fix
shapes never change the status; they let a paper table separate "the tool
missed" from "there was nothing for this tool class to find".

## 8. Role normalization

Bug entries in `bugs[].bug_introducing_commits` carry free-form `role`
spellings. `graph_scenario.normalize_bic_role` maps them onto five classes; the
rules are applied in this order after lower-casing:

| rule | class | examples in the suite |
|---|---|---|
| role missing or empty | `direct` | plain string entries such as `- c1` |
| contains `origin` | `origin` | `origin`, `origin_bic`, `old_origin_bic`, `origin_bug_introducing` |
| contains `reintroduc` | `reintroducing` | `reintroducing`, `direct_reintroduction`, `related_reintroducing`, `bug_reintroducing` |
| contains `contribut` | `contributing` | `contributing`, `contributing_bic` |
| starts with `direct` or contains `introduc` | `direct` | `direct`, `direct_squash_bic`, `merge_introducing`, `bug_introducing` |
| anything else (or a non-string value) | `other` | `distractor`, `refactoring` |

The classes `direct`, `reintroducing`, and `contributing` form the inferred
required set (section 1.4) and the set of expected hashes in the verifier's
basic blame check (`graph_verifier._verify_basic_blame`, GI703/GW703). The codes, including the informational `GI701` for a declared rewrite of the fault line, are tabulated in [validation.md](validation.md#verifier-findings-that-depend-on-a-declaration).
`origin` commits are never inferred as required: whether they count is a
scenario decision expressed through `required`, `acceptable_related`,
`related_origins`, or `related_but_not_correct`.

## 9. Worked examples

All examples use the same five-commit history:

```
c0  initial implementation
c1  adds the faulty helper (origin of the copied fault)
c2  copies the faulty line into the fixed file      <- direct BIC
c3  reformats the faulty line                        <- planted distractor
c4  bug-fixing commit
```

Predictions are written as logical ids; hashes behave identically.

### `exact_set`

```yaml
commit_level:
  evaluation_policy: exact_set
  required: [c2]
  known_distractors: [c3]
```

| predictions | TP | FP | FN | distractor hits | status |
|---|---|---|---|---|---|
| `[c2]` | c2 | – | – | – | PASS |
| `[c2, c3]` | c2 | c3 | – | c3 | FAIL |
| `[]` | – | – | c2 | – | FAIL |

### `direct_only` with `related_origins` and variants

```yaml
commit_level:
  evaluation_policy: direct_only
  required: [c2]
  related_origins: [c1]
evaluation_variants:
  - name: direct-only
    commit_level: {required: [c2]}
  - name: origin-aware
    commit_level: {required: [c2], related_origins: [c1]}
default_variant: direct-only
```

Predictions `[c2, c1]` give `false_positives = [c1]` under both variants, but
the diagnostics differ because a variant's `commit_level` replaces the base
one: with the default `direct-only` variant `c1` is not listed anywhere, so
`related_origin_hits = []` and `hard_false_positives = [c1]`; with
`--evaluation-variant origin-aware`, `related_origin_hits = [c1]` and
`hard_false_positives = []`. Status: **FAIL** with `direct-only` (strict
comparison), **PASS** with `origin-aware` (the name contains `origin`, so the
`related_origins` hit is tolerated).

### `reintroduction_direct`

History variant: c1 introduces the fault, c2 fixes it, c3 reintroduces it,
c4 fixes it again.

```yaml
commit_level:
  evaluation_policy: reintroduction_direct
  required: [c3]
  related_but_not_correct: [c1]
```

`[c3]` → PASS. `[c1]` → FAIL with `related_but_not_correct_hits = [c1]`,
`hard_false_positives = []`, `false_negatives = [c3]`. `[c1, c3]` → FAIL
(`c1` is a false positive and is never protected).

### `partial_credit`

```yaml
commit_level:
  evaluation_policy: partial_credit
  required: [c1, c2]
  minimum_required: 1
```

`[c2]` → PASS (`minimum_required_met: true`, `false_negatives = [c1]`,
`weighted_credit = 1.0`, `possible_credit = 2.0`, `credit_ratio = 0.5`).
`[c2, c3]` → FAIL (a false positive is never tolerated). `[]` → FAIL.

### `top_k`

```yaml
commit_level:
  evaluation_policy: top_k
  relevant: [c2]
  k_values: [1, 3, 5]
```

Predictions `c0` (rank 1), `c3` (rank 2), `c2` (rank 3):
`best_rank = 3`, `hit_at = {1: false, 3: true, 5: true}`, `mrr = 0.333`,
`status_k = 5` (largest k) → **PASS**. With `status_k: 1` added → **FAIL**,
same `hit_at`. With `k_values: [1]` only → `status_k = 1` → **FAIL**. Because
`required` is absent, `expected_bics` is inferred from the bug entries and the
result notes say so.

### `relaxed_with_related`

```yaml
commit_level:
  evaluation_policy: relaxed_with_related
  required: [c2]
  related_origins: [c1]
  related_but_not_correct: [c0]
```

`[c2, c1]` → PASS (`c1` is tolerated: `false_positives = [c1]` but
`hard_false_positives = []`). `[c2, c0]` → FAIL (`related_but_not_correct`
never protects). `[c1]` → FAIL (`c2` missing).

### `relaxed_with_credit`

```yaml
commit_level:
  evaluation_policy: relaxed_with_credit
  required: [c2]
  acceptable_related:
    - {commit: c1, reason: origin_bic, credit: 0.5}
```

`[c2, c1]` → PASS with `allowed_false_positives = [c1]`,
`acceptable_related_hits = [{commit: c1, credit: 0.5, reason: origin_bic}]`,
`weighted_credit = 1.0` (capped at `possible_credit = 1.0`). `[c1]` → FAIL
(`c2` missing) with `weighted_credit = 0.5`.

### `expect_no_bic`

```yaml
commit_level:
  evaluation_policy: exact_set
  expect_no_bic: true
```

`[]` → PASS. `[c1]` → FAIL (`false_positives = [c1]`). `[not-a-commit]` →
FAIL (`unknown_predictions`).

## 10. Report fields added for these semantics

| location | field |
|---|---|
| per scenario (JSON) | `top_k.status_k`, `known_distractor_hits`, `expect_no_bic`, `fix_shape`, additional `result_notes` |
| summary (JSON) | `known_distractor_hits`, `fix_shape_counts` |
| Markdown | `- Known distractor hits:`, `- Fix shapes (per BFC):`; table columns `Top-k`, `Distractor hits`, `Fix shape`; `## Scenario notes` section listing every scenario's `result_notes` |
| report `warnings` (JSON, Markdown `## Warnings`, CLI stderr) | oracle-related `result_notes` promoted with a `<scenario id>: ` prefix |
| validator | `GI086` (info) when `bug_introducing_commits` is empty and `expect_no_bic` is declared, instead of `GE084` |

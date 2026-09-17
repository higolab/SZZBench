# Decision: the direct / origin BIC contract (issue #3)

Status: **proposal for maintainer decision** (2026-09-17). Nothing in this document changes code or scenarios by itself; it fixes the vocabulary and the default rules that the scenario migration in issue #3 and the validator check in issue #16 will implement.

## 1. Problem

The graph suite records the *origin* of a copied or replayed fault in five different ways (`acceptable_related`, `related_origins`, `related_but_not_correct`, unlisted, `required`). Identical tool behaviour therefore passes in one scenario and fails in another, and the paper cannot state what "the BIC" means for copy propagation, rebases, squashes and reintroductions.

## 2. Definitions

For a bug entry with a bug-fixing commit *F* (evaluated against the first-parent history of *F*):

| term | definition | canonical role |
|---|---|---|
| **direct BIC** | a commit in the ancestry of *F* that introduces the faulty text (or the faulty behaviour, for omissions) into the file/location that *F* fixes | `direct` |
| **origin BIC** | an earlier commit from which the faulty text was copied, replayed (rebase, cherry-pick, squash, backport) or otherwise derived; it may or may not be an ancestor of *F* | `origin` |
| **contributing BIC** | a commit whose change is necessary for the fault to manifest but which does not itself write the faulty text (e.g. a caller change that makes a latent callee bug observable) | `contributing` |
| **reintroducing BIC** | a commit that re-establishes a previously fixed fault (revert of a fix, partial revert, replay after a fix) | `reintroducing` |
| **behaviour-preserving rewrite** | a commit that changes the faulty line's text without changing behaviour (formatting, rename, comment, extraction) | not a BIC → `related_but_not_correct` |

Role spellings used today (23 for bug entries) are mapped onto the four canonical roles by the normalisation introduced in issue #15 (`normalize_bic_role`); scenario files should nevertheless be migrated to the canonical spellings (issue #19).

## 3. Evaluator mechanics (verified against `evaluator.py`, 2026-09-17)

| list | effect on PASS/FAIL |
|---|---|
| `required` | every entry must be predicted |
| `acceptable_related` | never counts as a false positive; carries `credit` |
| `related_origins` | not a false positive under `relaxed_with_related`, `relaxed_with_credit`, or any variant whose name contains `origin` or `related`; a false positive under plain `exact_set`/`direct_only`/`reintroduction_direct` |
| `related_but_not_correct` | always a false positive (only excluded from *hard* false positives, i.e. it is a diagnostic bucket) |
| unlisted | hard false positive |

`direct_only` and `reintroduction_direct` share the exact-set comparison; they differ only in how the scenario author defined `required`.

## 4. Decision (proposed default rules)

**D1 — default variant is direct-only.** `expected_szz.commit_level.required` (or the `default_variant`) lists the direct BICs of the evaluated BFC(s), plus contributing and reintroducing BICs when the bug entry declares them. Origins are never in the default `required`.

**D2 — every declared origin is listed as `related_origins`.** A BIC entry with role `origin` must appear in `related_origins` of the default `commit_level`. Consequence: predicting the origin is a plain false positive under the default variant, but not a *hard* one, and the origin-aware variant (D3) can accept it without a second oracle.

**D3 — every scenario with an origin provides an `origin-aware` variant.** `evaluation_variants` contains `origin-aware` with `evaluation_policy: relaxed_with_related`, the same `required` set, and the origins as `acceptable_related` with `credit: 0.5` (the convention already used by SZZG-0022). Scenarios that want to *require* the origin add a third variant `origin-required` (`exact_set`, `required` = direct ∪ origin). Adapters choose the variant with `--evaluation-variant`.

**D4 — copy and replay commits are direct BICs.** The commit that copies, cherry-picks, rebases, squashes or backports the faulty text into the history of *F* is the direct BIC for *F*; the source commit is the origin. This is the rule SZZG-0020/0022/0047 already follow; SZZG-0025/0027/0028 must be aligned with it (see §5).

**D5 — behaviour-preserving rewrites are never BICs.** Formatting, identifier renames, comment insertion, method extraction and similar edits of the faulty line are `related_but_not_correct`. This is the rule SZZG-0008/0013 follow; SZZG-0024 must be aligned with it (its required "direct BIC" r2 only appends a comment; r1 introduced the fault).

**D6 — an attempted fix that introduces a new fault is a direct BIC of that new fault.** When the new fault is distinguishable (SZZG-0030: the `||` regression written by c2), model it as a second bug entry with its own BIC/BFC; when it is not distinguishable, list the commit as `contributing`.

**D7 — reintroductions.** The reintroducing commit is `required`; the original BIC is `related_origins`; the original fix is `related_but_not_correct`. `reintroduction_direct` stays an alias of exact-set comparison and should be documented as such.

**D8 — history rewriting.** Replayed commits (rebase, squash) are direct; the pre-rewrite commits are origins and therefore go to `related_origins`, not to `related_but_not_correct` as most rebase scenarios do today. Whether the pre-rewrite commits are reachable in the generated repository is a controlled scenario property (issue #17, `ref_lifecycle`) and must be stated in the README; it does not change the oracle.

**D9 — multiple bugs sharing a BFC.** Until the evaluator scores per bug, the scenario-level `required` set is the union of the per-bug direct BICs of the evaluated BFC(s) (SZZG-0018 → `{c0, c1}`; SZZG-0034 already conforms).

**D10 — validation.** The lint of issue #16 flags a BIC entry with role `origin*` that is covered by no `expected_szz` list; after D2/D3 it should additionally require that origins appear in `related_origins` of the default commit level and that an `origin-aware` variant exists.

## 5. Migration table

| scenario | today | after D1–D9 |
|---|---|---|
| SZZG-0014, SZZG-0015, SZZG-0017 | origin c0 declared, unlisted | add `related_origins: [c0]`, add `origin-aware` variant |
| SZZG-0016 | origin as `acceptable_related` in default | move to `related_origins`; keep `acceptable_related` in the `origin-aware` variant |
| SZZG-0018 | `required: [c1]` for two bugs | `required: [c0, c1]` (D9) until per-bug scoring exists |
| SZZG-0019, SZZG-0020 | `related_origins` | already conform; add `origin-aware` variant where missing |
| SZZG-0022 | direct-only / origin-aware / relaxed-with-credit variants | reference implementation; drop the redundant `relaxed-with-credit` variant or keep as alias |
| SZZG-0024 | required r2 (comment-only rewrite), r1 not correct | required r1; r2 → `related_but_not_correct` (D5) |
| SZZG-0025 | required c1 (origin) | required c2 (copy), `related_origins: [c1]`, `origin-aware` variant (D4) |
| SZZG-0027 | required c1; c2 (copy) and c3 (rename) unlisted | required c2, `related_origins: [c1]`, `related_but_not_correct: [c3]` |
| SZZG-0028 | required {c1, c3}; copy c2 unlisted | required {c2, c3}, `related_origins: [c1]`; `origin-required` variant {c1, c2, c3} |
| SZZG-0030 | c2 (attempted fix writing the fixed line) unlisted | second bug entry B002 (BIC c2, BFC c3) or `contributing` (D6) |
| SZZG-0047, SZZG-0055–0058, SZZG-0064–0083 | pre-rewrite commits as `related_but_not_correct` | move to `related_origins`; add `origin-aware` variant (D8) |
| SZZG-0061 | manual cherry-pick, origin c1 unlisted | add `cherry_pick_of: c1`, `related_origins: [c1]` |
| SZZG-0084–0091 (reintroduction) | mixed | reintroducing commit required; original BIC `related_origins`; original fix `related_but_not_correct` (D7) |

## 6. Open points for the maintainers

1. Credit value for origins in the `origin-aware` variant (0.5 as in SZZG-0022, or 0).
2. Whether `origin-required` variants are generated for every origin scenario or only where the README argues for root-cause semantics.
3. Whether the default variant should be renamed from implicit `commit_level` to an explicit `direct-only` variant everywhere (clearer for adapters; larger diff).

# Decision: the direct / origin BIC contract (issue #3)

Status: **decided** (2026-09-18; proposed 2026-09-17). D1-D9 are adopted as written and the four open points of §6 are answered in §7. The scenario migration is being carried out in two steps: the semantic corrections of §5 first, then the mechanical `related_origins` / `origin-aware` sweep across the remaining scenarios and the D10 lint.

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

**D4 — copy and replay commits are direct BICs; pure moves are not.** The commit that copies, cherry-picks, rebases, squashes or backports the faulty text into the history of *F* is the direct BIC for *F*; the source commit is the origin. This is the rule SZZG-0020/0022/0047 already follow; SZZG-0025/0027/0028 must be aligned with it (see §5). The boundary between the three kinds of propagation is:

- *Movement* — a rename or move of a file or method after which the source location no longer contains the fault and the number of faulty instances stays one. Behaviour-preserving, therefore **not a BIC** (D5); the original commit remains the direct BIC (SZZG-0003, 0004, 0005, 0010).
- *Copying into a new instance* — after the commit the fault exists at an additional location, whether or not the source keeps it. The copying commit is the **direct BIC of the new instance**; the source commit is that instance's origin (the SZZG-0014–0028 family).
- *Replay* — cherry-pick, rebase, squash or backport into another history. The replayed commit is the direct BIC for BFCs in that history; the source commit is the origin (SZZG-0047, 0049, 0050, the G5 scenarios).

A commit that moves *and* duplicates (SZZG-0007: c2 moves `contains` to `RangeUtils.java` and copies the faulty line into `Bounds.within`) is therefore not a BIC for the moved instance but the direct BIC for the duplicated instance. Under D9 the scenario-level `required` of a BFC that fixes both instances is the union `{c1, c2}`. PR #28 keeps SZZG-0007's pre-D4 contract (`required: [c1]`, c2 `related_but_not_correct`), which is consistent with the oracle it states; adopting D4 means migrating it (or splitting the duplicate into its own scenario) — see §5 and open point 4. Scenarios that want the *origin* accepted or required *in addition to* the direct copy express that through the `origin-aware` / `origin-required` variants (D3), never by changing the default; neither variant lets an origin-only prediction replace the direct BIC (with SZZG-0022's `origin-aware` variant, predicting `{c1}` alone fails with `false_negatives: [c2]`, while `{c2}` and `{c1, c2}` pass). Origin-only acceptance would need a separately defined variant and is not proposed here.

**D5 — behaviour-preserving rewrites are never BICs.** Formatting, identifier renames, comment insertion, method extraction and similar edits of the faulty line are `related_but_not_correct`. This is the rule SZZG-0008/0013 follow; SZZG-0024 must be aligned with it (its required "direct BIC" r2 only appends a comment; r1 introduced the fault).

**D6 — an attempted fix that introduces a new fault is a direct BIC of that new fault.** When the new fault is distinguishable (SZZG-0030: the `||` regression written by c2), model it as a second bug entry with its own BIC/BFC; when it is not distinguishable, list the commit as `contributing`.

**D7 — reintroductions.** The reintroducing commit is `required`; the original BIC is `related_origins`; the original fix is `related_but_not_correct`. `reintroduction_direct` stays an alias of exact-set comparison and should be documented as such.

**D8 — history rewriting.** Replayed commits (rebase, squash) are direct; the pre-rewrite commits are origins and therefore go to `related_origins`, not to `related_but_not_correct` as most rebase scenarios do today. Whether the pre-rewrite commits are reachable in the generated repository is a controlled scenario property (issue #17, `ref_lifecycle`) and must be stated in the README; it does not change the oracle.

**D9 — multiple bugs sharing a BFC.** Until the evaluator scores per bug, the scenario-level `required` set is the union of the per-bug direct BICs of the evaluated BFC(s) (SZZG-0018 → `{c0, c1}`; SZZG-0034 already conforms).

**D10 — validation.** The lint of issue #16 flags a BIC entry with role `origin*` that is covered by no `expected_szz` list; after D2/D3 it should additionally require that origins appear in `related_origins` of the default commit level and that an `origin-aware` variant exists.

## 5. Migration table

| scenario | today | after D1–D9 |
|---|---|---|
| SZZG-0005 (PR #28) | required c1; move commit c2 `related_but_not_correct` | already conforms (pure move, D5) |
| SZZG-0007 (PR #28) | required c1; move-and-copy commit c2 `related_but_not_correct` | **done**: `required: [c1, c2]` (c1 for the moved instance, c2 for the duplicated instance); not split (§7.4) |
| SZZG-0014, SZZG-0015, SZZG-0017 | origin c0 declared, unlisted | add `related_origins: [c0]`, add `origin-aware` variant |
| SZZG-0016 | origin as `acceptable_related` in default | move to `related_origins`; keep `acceptable_related` in the `origin-aware` variant |
| SZZG-0018 | `required: [c1]` for two bugs | **done**: `required: [c0, c1]` (D9) until per-bug scoring exists; no origin-aware variant, the origin is required (§7) |
| SZZG-0019, SZZG-0020 | `related_origins` | already conform; add `origin-aware` variant where missing |
| SZZG-0022 | direct-only / origin-aware / relaxed-with-credit variants | reference implementation; drop the redundant `relaxed-with-credit` variant or keep as alias |
| SZZG-0024 | required r2 (comment-only rewrite), r1 not correct | **done**: required r1; `related_origins: [f1]`; r2 and f2 → `related_but_not_correct` (D5) |
| SZZG-0025 | required c1 (origin) | **done**: required c2 (copy), `related_origins: [c1]`, `origin-aware` variant (D4) |
| SZZG-0027 | required c1; c2 (copy) and c3 (rename) unlisted | **done**: required c2, `related_origins: [c1]`, `related_but_not_correct: [c3]` |
| SZZG-0028 | required {c1, c3}; copy c2 unlisted | **done**: required {c2, c3}, `related_origins: [c1]`, `origin-aware` variant; no `origin-required` variant (§7.2) |
| SZZG-0030 | c2 (attempted fix writing the fixed line) unlisted | **done**: second bug entry B002 (BIC c2, BFC c3); `required: [c1, c2]` by D9 |
| SZZG-0047, SZZG-0055–0058, SZZG-0064–0083 | pre-rewrite commits as `related_but_not_correct` | move to `related_origins`; add `origin-aware` variant (D8) |
| SZZG-0061 | manual cherry-pick, origin c1 unlisted | **done**: `cherry_pick_of: c1` (inert - the generated trees and messages are unchanged), `related_origins: [c1]`, `origin-aware` variant |
| SZZG-0084–0091 (reintroduction) | mixed | reintroducing commit required; original BIC `related_origins`; original fix `related_but_not_correct` (D7) |

## 6. Open points for the maintainers

1. Credit value for origins in the `origin-aware` variant (0.5 as in SZZG-0022, or 0).
2. Whether `origin-required` variants are generated for every origin scenario or only where the README argues for root-cause semantics.
3. Whether the default variant should be renamed from implicit `commit_level` to an explicit `direct-only` variant everywhere (clearer for adapters; larger diff).
4. Move-and-duplicate histories (SZZG-0007): keep one bug entry with the union oracle `{c1, c2}` under D4/D9, or split the duplicated instance into a separate scenario so that each scenario tests exactly one propagation kind.

## 7. Answers (2026-09-18)

1. **Credit 0.5.** It is already SZZG-0022's convention, and the number is only ever reported as `credit_ratio`, never as a pass; keeping one value means an origin hit reads the same everywhere.
2. **`origin-required` only where the README argues for root-cause semantics.** Generating it everywhere would publish a third oracle for every copy scenario without any scenario claiming it is the interesting one.
3. **The default variant stays implicit.** Naming it in all 114 graph scenarios is a large diff for a rename; `expected_szz.commit_level` already *is* the default, and the variants that exist are named.
4. **SZZG-0007 keeps one bug entry with the union oracle `{c1, c2}`.** Splitting it would lose exactly the property the scenario exists for: that one commit both moves and duplicates, and the contract answers the two halves differently.

Two clarifications the migration produced, which are part of the decision:

- **An origin that is already `required` needs no `origin-aware` variant.** SZZG-0018's `c0` is the direct BIC of one bug entry and the origin of the other; the variant would be identical to the default, so D3 does not apply when the origin is in `required`.
- **D6 splits a bug only when both effects are observable.** SZZG-0030's `c2` was measured to repair one fault (`contains(5,5,7)`: false to true) and introduce another (`contains(99,5,7)`: false to true) in the same commit, which is what makes the second bug entry a measurement rather than a reading of the diff.

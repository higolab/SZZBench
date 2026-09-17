# Decision matrix: consolidation candidates (issue #12)

Status: **decision aid, not a decision** (2026-09-17). The 38 MERGE / 13 DELETE labels from the scenario review are proposals; the validation follow-up showed that some pairs differ in DAG size, origin side or evaluation contract. This matrix records, per candidate, what a tool can actually observe and what the scenario is meant to test, so that each item can be decided after the confirmed defects (issues #1, #2, #4–#10) are fixed.

## 1. Decision procedure

1. Fix confirmed defects first (oracles, compile errors, unrealized histories). Several "duplicates" stop being duplicates once repaired (e.g. SZZG-0067 as a real conflict, SZZG-0111 with recorded file modes).
2. Compute equivalence classes over generated repositories using the features tools consume: parent DAG, trees per commit, final refs, and (separately) commit messages. Patch-sequence hashes alone are insufficient (they wrongly grouped SZZG-0058/0084).
3. Within a class, keep one scenario per *distinct stated factor*. If two scenarios in one class differ only in narrative, either differentiate the content with generator features from issue #17 (squash message, trailers, ref lifecycle) or merge.
4. Keep blame-trivial scenarios as labelled *controls* when they exercise a filter or a parent-handling choice that tools can get wrong; delete only when no failure mode is testable.

Columns: **visible difference** = what a tool sees in the repository (DAG / refs / messages / code); **oracle** = whether the expected answer differs; **blame** = plain first-parent blame outcome (T exact, T+x extra candidates, N miss, ghost); **decision** = proposed default, to be confirmed.

## 2. Delete candidates

| scenario | reason in review | what changed since | decision |
|---|---|---|---|
| SZZ-0058 | same omission template as SZZ-0053; no resource/close in code | — | **delete** (or rewrite with a real `Closeable`) |
| SZZ-0070 | same template; `canStart(ready)` is a minimal guard | validation: weak example, not absent | **repair** (real two-state check) or delete |
| SZZ-0088 | "reformat" adds `final` | — | **retitle** ("class modifier change after BIC") — the change is behaviour-neutral and is a legitimate noise commit |
| SZZ-0091 | removes nothing; leaking comment | — | **repair** as a real dead-code removal (add dead code in c0/c1, remove it in c2) or delete |
| SZZ-0095, SZZ-0098 | never compile | repairable (#10) | **repair**, keep |
| SZZ-0108 | no CRLF rewrite; text ops normalize newlines | `line_ending` option planned (#18) | **rebuild** once #18 lands; otherwise delete |
| SZZ-0123 | — | withdrawn (fixes two expressions on one line) | **keep**, fix factor |
| SZZ-0137, SZZ-0142 | inverted oracles | being repaired as two-BIC scenarios (#1) | **keep** (repaired) |
| SZZ-0167 | 2-commit duplicate of SZZ-0160 | — | **delete** after SZZ-0160 is rebuilt so that the fix lives in the caller |
| SZZG-0054 | commit-level identical to linear c1→c3 | — | **repair** (add the release-side unfixed BFC as a second bug entry, needs per-bug scoring) or delete |
| SZZG-0116 | no `commit_level`; entity-level unimplemented | `expect_no_bic`/notes in #15 | **gate**: keep only when entity-level evaluation exists; otherwise delete |

## 3. Merge candidates — normal suite

| candidate → target | factor tested | visible difference | oracle | blame | decision |
|---|---|---|---|---|---|
| SZZ-0044 → SZZ-0012 | `&&`→`\|\|` flip | code names only | same | T / T | **merge** |
| SZZ-0082 → SZZ-0081 | formatting after BIC | same 2-line split of the faulty expression | same | N / N | **merge** (keep 0081) |
| SZZ-0087 → SZZ-0104 | method addition after BIC | 0087's c2 is not valid Java | same | T+x | **merge** into the valid one |
| SZZ-0109 → SZZ-0085 | comment inserted, BFC removes it | none | same | T+x | **merge** |
| SZZ-0120 → SZZ-0115 | BFC adds helper | none | same | T | **merge** |
| SZZ-0146 → SZZ-0133 | duplicate statement text | 0146 has only a commit-level oracle | same | T | **merge** (keep 0133) |

## 4. Merge candidates — graph suite

| candidate → target | factor tested | visible difference | oracle | blame | decision |
|---|---|---|---|---|---|
| SZZG-0002 → SZZG-0001 | move+fix vs rename+fix in one BFC | directory changes; `package` not updated (bug) | same | T | **keep both as controls** after fixing the package; rename vs move are different rename-detection inputs |
| SZZG-0004 → SZZG-0010 | move between BIC and BFC | 0010 adds package rename | same | T | **merge** (0010 is the superset) |
| SZZG-0013 → SZZG-0008 | semantic-preserving rewrite | 0013 lacks `related_but_not_correct` | **same acceptance condition**: with predictions `{c1, c2}` both FAIL with `false_positives: [c2]` (under `exact_set` a `related_but_not_correct` entry is still a false positive); only the diagnostic bucket differs (related-but-not-correct hit in 0008, hard false positive in 0013) | N | **merge** as a redundant history; give the survivor `related_but_not_correct: [c2]` for the diagnostic (D5) |
| SZZG-0015 → SZZG-0018 | copy then fix original later | DAG/tree-equivalent | 0018 has two bugs | T | **merge** into 0018 once per-bug oracle is fixed (D9) |
| SZZG-0020 → SZZG-0022 | direct vs origin | same DAG; 0022 has variants | same | T | **merge** (0022 superset) |
| SZZG-0021 ↔ SZZG-0109 | file deletion as fix / file deletion | 0021 has clone metadata | similar | T | **merge** into one file-deletion scenario with candidates |
| SZZG-0025 → SZZG-0022 | copy propagation | same shape; contradictory oracle | differs (D4 fixes it) | N | **merge** after D4 |
| SZZG-0031 → SZZG-0032 | one BIC, multiple BFCs | DAG/tree-equivalent | same | T | **merge** |
| SZZG-0036 → SZZG-0029 | partial then complete fix | 0036 adds a test-note commit | same | N | **merge** |
| SZZG-0037 → SZZG-0034 | one BFC, multiple BICs | same DAG shape | **different contract** (independent bugs vs composite fault) | T | **keep both** once per-bug scoring exists; until then merge |
| SZZG-0038 → SZZG-0040 | context-only BIC | same inline-constant trick | same | N | **merge** |
| SZZG-0045 → SZZG-0059 | merge commit as BIC | 0045 adds text in neither parent; 0059 discards a branch change | same idea, different mechanism | T / N | **keep both** (different failure modes: evil-merge text vs discarded change) |
| SZZG-0049, 0056, 0062 → SZZG-0050 | backport / cross-branch fix | same pattern, **different DAG sizes** (0050 larger) | labels differ | T | **merge 0056 and 0062**; keep 0049 (cherry-picked BFC) after fixing its `bug_instances` |
| SZZG-0055 → SZZG-0057 | rebase after main changes | branch name, one noise commit | same | T | **merge** |
| SZZG-0060 → SZZG-0043 | BFC on main after merge | DAG/tree-equivalent | same | T | **merge** |
| SZZG-0061 → SZZG-0048 | cherry-picked BIC | 0061 lacks `cherry_pick_of`; 0048's BFC is on the wrong branch | both need repair | T | **repair 0048** (BFC on release) and merge 0061 into it |
| SZZG-0066 → SZZG-0057 | "conflict" flag only | one docs commit fewer | same | T | **merge** unless rebuilt as a real conflict (#17) |
| SZZG-0067 → SZZG-0058 | dangling `rebase_of` | linear history | same | T | **rebuild** as a real conflict-resolving fix when #17 lands; otherwise merge |
| SZZG-0069 → SZZG-0076 | split BIC vs two BICs replayed | main line identical; **origin side differs** (visible only via `feature` ref) | same required set | N | **keep both** as an origin-aware pair, document the ref condition |
| SZZG-0070 → SZZG-0047 | interactive squash | DAG/tree-equivalent | same | T | **merge** (or differentiate with a GitHub-style squash message, #17) |
| SZZG-0071 → SZZG-0068 | replay differs from origin | same concept | same | T | **merge** |
| SZZG-0072 → SZZG-0047 | dropped BIC | DAG/tree-equivalent; r2 not a pure replay | same position | T | **differentiate** (delete `feature` ref via `ref_lifecycle`, make r2 a pure replay) or merge |
| SZZG-0077 → SZZG-0032 | rebased BIC, multiple BFCs | unreachable feature branch added | same | T | **merge** |
| SZZG-0078 → SZZG-0064 | message reveals origin | DAG/tree-equivalent; message differs; trailer YAML-only | same | T | **differentiate** by writing a real `Rebased-from:`/cherry-pick trailer (#17); otherwise merge |
| SZZG-0082 → SZZG-0064 | generated-file update | inert extra file | same | T | **repair** (let the noise touch the fault file) or merge |
| SZZG-0084 → SZZG-0086 | "partial" revert is full | different DAG from 0058 (not a duplicate) | same | T | **repair** as a real partial revert or merge |
| SZZG-0089 → SZZG-0086 | revert-of-revert "with conflict" | no conflict possible | same | T | **rebuild** with `resolution` (#17) or merge |
| SZZG-0091 → SZZG-0088 | multiple BICs + partial revert | origin split in two commits | same | T | **merge** |
| SZZG-0094 → SZZG-0100 | issue-tagged commit series | 0094 carries `ISSUE-101` in BIC/BFC messages (0100 does not) | same | T | **keep 0094**; repair 0100's messages, then decide |
| SZZG-0096 → SZZG-0115 | top-k within a work item | policy inside G7 | same | T | **merge** into the policy scenario |
| SZZG-0111 → SZZG-0110 | chmod-only intermediate | empty commit today | same | T | **repair** with recorded file modes (#18), then keep |

## 5. Structurally identical groups (normal suite)

Same roles, operation sequence, oracle shape and fault text; they differ only in the distractor content. After the S3 template repair (issue #6) most become blame-trivial *candidate-selection controls*; keep one representative per noise kind and record the others as variants in the README of the survivor.

| group | representative to keep |
|---|---|
| SZZ-0085, 0086, 0087, 0089, 0090 (insertions after BIC) | 0085 (comment) and 0090 (guard) — semantically different noise |
| SZZ-0096, 0102, 0103, 0104, 0105 | 0103 (clean distractor) and 0096 (lambda rewrite, N) |
| SZZ-0081, 0083, 0084, 0088 (formatting family) | 0081 and 0083 (`blame -w` discriminator) |
| SZZ-0107, 0108, 0111, 0116 | 0107, 0111, 0116 (0108 handled above) |
| SZZ-0094, 0101, 0110 | 0110 (large noise) after compile fixes |
| SZZ-0127, 0128, 0129 | 0128 (extract) and 0129 (inline control) |

## 6. Expected outcome

Applying the defaults above yields roughly 25–30 merges and 4–6 deletions instead of 38/13, and turns a further 8–10 candidates into repairs. The suite size after consolidation is therefore ~155–160 before the additions of issues #20–#24, not 143. The exact number is a result of the per-item decisions, not a target.

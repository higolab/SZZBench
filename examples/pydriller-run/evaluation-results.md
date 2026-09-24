# SZZBench Evaluation Results

## Summary

- Total scenarios: 281
- PASS: 162
- FAIL: 119
- True positives: 236
- False positives: 67
- False negatives: 107
- Allowed false positives: 0
- Hard false positives: 53
- Related origin hits: 1
- Related-but-not-correct hits: 13
- Known distractor hits: 23
- Branch-level failures: 1 of 3 scenario(s) with a branch-level oracle
- Fix shapes (per BFC): empty_first_parent 1, addition_only 16, modifies 276
- Weighted credit: 236.000/343.000
- Precision: 0.779
- Recall: 0.688

## Warnings

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0115: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.
- SZZG-0136: Requested evaluation variant 'default' is not defined; using commit_level.
- SZZG-0140: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.

## Results

| Scenario | Status | Suite | Policy | Variant | Category | Expected BICs | Actual BICs | TP | FP | FN | Allowed FP | Predictions | Top-k | Distractor hits | Fix shape |
|---|---:|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|
| SZZ-0005 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0006 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0012 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0014 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0015 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0021 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0028 | FAIL | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | 2 | - | - | c2:modifies |
| SZZ-0044 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0047 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0050 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0053 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0070 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0076 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0078 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0079 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0080 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0081 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0082 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0083 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0084 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0085 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0086 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0087 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0088 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0089 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0090 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0091 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0092 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0093 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0094 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0095 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0096 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0098 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0099 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0100 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0101 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0102 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0103 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0104 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0105 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0107 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0108 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0109 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0110 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0111 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0112 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0113 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0114 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0115 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0116 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0117 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0118 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0119 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0120 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0121 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | 2 | - | - | c2:modifies |
| SZZ-0122 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0123 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0124 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0125 | PASS | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0127 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0128 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0129 | PASS | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0130 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0132 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c2 | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0133 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0134 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0136 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c2 | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0137 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0142 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0146 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0154 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0155 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0156 | PASS | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0158 | PASS | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0159 | PASS | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0160 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0166 | PASS | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0168 | PASS | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0169 | FAIL | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0170 | PASS | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0171 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0172 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0173 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c0 | - | - | - | c0 | - | 0 | - | - | c1:addition_only |
| SZZ-0174 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0175 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0176 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0177 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0178 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c3 | - | c3 | c1 | - | 1 | - | c3 | c4:modifies |
| SZZ-0179 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZ-0180 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c0 | c0 | c0 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0181 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0182 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0183 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0184 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0185 | PASS | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0186 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0187 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | 3 | - | - | c3:modifies |
| SZZ-0188 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | 2 | - | - | c3:modifies |
| SZZ-0189 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c3:modifies |
| SZZ-0190 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0191 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0192 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c2, c4 | c3, c4 | c4 | c3 | c2 | - | 2 | - | - | c5:modifies |
| SZZ-0193 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0194 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0195 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c4 | c4 | c4 | - | c1 | - | 1 | - | - | c5:modifies |
| SZZ-0196 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0197 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c5 | c3, c5 | c5 | c3 | c1 | - | 2 | - | - | c6:modifies |
| SZZ-0198 | FAIL | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0199 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0200 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0201 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0202 | PASS | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0203 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0204 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0205 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0206 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0207 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0208 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0209 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c4 | - | c4 | c1 | - | 1 | - | c4 | c5:modifies |
| SZZ-0210 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c4 | - | c4 | c1 | - | 1 | - | c4 | c5:modifies |
| SZZ-0211 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c5 | - | c5 | c1 | - | 1 | - | c5 | c6:modifies |
| SZZ-0212 | PASS | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c1, c3 | c1, c3 | - | - | - | 2 | - | - | c4:modifies |
| SZZ-0213 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c0, c1 | c1 | c0 | c3 | - | 2 | - | - | c4:modifies |
| SZZ-0214 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | - | - | - | c1, c3 | - | 0 | - | - | c4:addition_only |
| SZZ-0215 | FAIL | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c2, c3 | c3 | c2 | c1 | - | 2 | - | - | c4:modifies |
| SZZ-0216 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c2, c3 | c3 | c2 | c1 | - | 2 | - | - | c4:modifies |
| SZZ-0217 | FAIL | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0218 | FAIL | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c1, c2, c3 | c1, c3 | c2 | - | - | 3 | - | - | c4:modifies |
| SZZ-0219 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1, c4 | c3, c4 | c4 | c3 | c1 | - | 2 | - | - | c5:modifies |
| SZZ-0220 | FAIL | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | 4 | - | - | c4:modifies |
| SZZ-0221 | FAIL | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c1 | c1 | - | c3 | - | 1 | - | - | c4:modifies |
| SZZ-0222 | FAIL | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | c0 | - | c0 | c1, c3 | - | 1 | - | - | c4:modifies |
| SZZ-0223 | FAIL | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0224 | FAIL | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0225 | FAIL | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c2, c3 | c3 | c2 | c1 | - | 2 | - | - | c4:modifies |
| SZZG-0001 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c0, c1 | c1 | c0 | - | - | 2 | - | - | c2:modifies |
| SZZG-0002 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0003 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0004 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0005 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0006 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0007 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c2 | c2 | c2 | - | c1 | - | 2 | - | - | c3:modifies |
| SZZG-0008 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0009 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0010 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0011 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0012 | PASS | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0013 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0014 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0015 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0016 | FAIL | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c0, c1 | c1 | c0 | - | - | 2 | - | - | c2:modifies |
| SZZG-0017 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0018 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c0, c1 | c0, c1 | c0, c1 | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0019 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0020 | PASS | advanced-scenarios | direct_only | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0021 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0022 | PASS | advanced-scenarios | exact_set | direct-only | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0023 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r2 | r2 | r2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0024 | FAIL | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r1 | r2 | - | r2 | r1 | - | 1 | - | - | c4:modifies |
| SZZG-0025 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0026 | PASS | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0027 | FAIL | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c3 | - | c3 | c2 | - | 1 | - | - | c4:modifies |
| SZZG-0028 | FAIL | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2, c3 | c3 | c3 | - | c2 | - | 1 | - | - | c4:modifies |
| SZZG-0029 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1, c2 | c1 | c2 | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0030 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0031 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0032 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0033 | PASS | advanced-scenarios | partial_credit | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0034 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0035 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0 | - | c0 | c1 | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0036 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1, c3 | c1 | c3 | - | - | 2 | - | - | c3:modifies, c4:modifies |
| SZZG-0037 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0038 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1 | c1 | c0 | c2 | - | 2 | - | - | c3:modifies |
| SZZG-0039 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0040 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c2 | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0041 | PASS | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0042 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | - | - | - | c1 | - | 0 | - | - | c3:empty_first_parent |
| SZZG-0043 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0044 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0045 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0046 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | - | - | - | c1 | - | 0 | - | - | c4:modifies |
| SZZG-0047 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0048 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0049 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0050 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0051 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0052 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | a1 | a1 | a1 | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0053 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c2 | c2 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0054 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0055 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0056 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0057 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0058 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0059 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c0 | - | c0 | c3 | - | 1 | - | - | c4:modifies |
| SZZG-0060 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0061 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0062 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0064 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0065 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0066 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0067 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0068 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0069 | FAIL | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r2 | r2 | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0070 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0071 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0072 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | r2 | r2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0073 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | r2 | r2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0075 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | f1 | f1 | - | - | - | 1 | - | - | f2:modifies |
| SZZG-0076 | FAIL | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r2 | r2 | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0077 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 2 | - | - | c3:modifies, c4:modifies |
| SZZG-0078 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0081 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0082 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0083 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0084 | PASS | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0085 | PASS | advanced-scenarios | exact_set | reintroduction-direct | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0086 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0088 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0089 | FAIL | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c4 | - | c4 | c3 | - | 1 | - | - | c5:modifies |
| SZZG-0090 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c5 | c5 | c5 | - | - | - | 1 | - | - | c6:modifies |
| SZZG-0091 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c4 | c4 | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0093 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0094 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0095 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0096 | PASS | advanced-scenarios | top_k | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | 1 | rank 1 (k=1) | - | c4:modifies |
| SZZG-0097 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0098 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0099 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0100 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0101 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0102 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0103 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0104 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0105 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0107 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0108 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0109 | FAIL | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c0 | c0, c1 | c0 | c1 | - | - | 3 | - | - | c4:modifies |
| SZZG-0110 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0111 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0112 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0113 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0114 | PASS | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0115 | PASS | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c1 | c1 | - | - | - | 1 | rank 1 (k=5) | - | c4:modifies |
| SZZG-0116 | PASS | advanced-scenarios | exact_set | - | Evaluation policy variants | c1 | c1 | c1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0117 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1, c4 | c4 | c4 | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0118 | FAIL | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0119 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0120 | FAIL | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c2 | c2 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0121 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2, r1 | c2 | c2 | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0122 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0123 | PASS | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | f1 | f1 | - | - | - | 1 | - | - | f2:modifies |
| SZZG-0124 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0125 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0126 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0127 | PASS | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c4 | c4 | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0128 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0129 | PASS | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | q1 | q1 | q1 | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0130 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0131 | PASS | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | r1 | r1 | r1 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0132 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c2 | - | c2 | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0133 | FAIL | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZG-0134 | FAIL | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0 | - | c0 | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0135 | FAIL | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0136 | FAIL | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0137 | PASS | advanced-scenarios | exact_set | - | Evaluation policy variants | c0 | c0 | c0 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0138 | PASS | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c2, c3 | c1, c2 | c1, c2 | - | c3 | - | 2 | - | - | c4:modifies |
| SZZG-0139 | PASS | advanced-scenarios | partial_credit | - | Evaluation policy variants | f1, m1 | f1, m1 | f1, m1 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0140 | FAIL | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c2 | - | c2 | c1 | - | 1 | miss (k=1) | c2 | c4:modifies |
| SZZG-0141 | PASS | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c3, c4 | c3, c4 | c3, c4 | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0142 | PASS | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c2 | c2 | c2 | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0143 | FAIL | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1, r1 | c1 | r1 | - | - | 2 | - | r1 | c3:modifies, r2:modifies |
| SZZG-0144 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2, c4 | c4 | c4 | - | c2 | - | 1 | - | - | c6:modifies |
| SZZG-0145 | FAIL | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0146 | FAIL | advanced-scenarios | exact_set | full-cause | Evaluation policy variants | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0147 | FAIL | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3, c4 | c4 | c4 | - | c3 | - | 1 | - | - | c5:modifies |
| SZZG-0148 | FAIL | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c3, c4 | c1 | c1 | - | c3, c4 | - | 1 | - | - | c5:modifies |
| SZZG-0149 | FAIL | advanced-scenarios | partial_credit | - | Branch, merge, cherry-pick, backport, and release branches | c1, c3, c5 | c1 | c1 | - | c3, c5 | - | 1 | - | - | c7:modifies |
| SZZG-0150 | FAIL | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c4 | c4 | c4 | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0151 | FAIL | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c4, c5 | c5 | c5 | - | c4 | - | 1 | - | - | c6:modifies |
| SZZG-0152 | FAIL | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1, c4 | c4 | c4 | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0153 | FAIL | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | c1 | - | 1 | - | - | c4:modifies |

## Scenario notes

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0115: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.
- SZZG-0136: Requested evaluation variant 'default' is not defined; using commit_level.
- SZZG-0140: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.

# SZZBench Evaluation Results

## Summary

- Total scenarios: 279
- PASS: 28
- FAIL: 251
- Tool errors: 0
- Missing prediction records: 0
- Predictions made on another repository: 0
- True positives: 263
- False positives: 245
- Unknown predictions (counted as false positives): 0
- False negatives: 78
- Allowed false positives: 0
- Hard false positives: 224
- Related origin hits: 1
- Related-but-not-correct hits: 20
- Known distractor hits: 32
- Branch-level failures: 3 of 3 scenario(s) with a branch-level oracle
- Attribution failures: 8 of 9 scenario(s) with several bug-fixing commits
- Fix shapes (per BFC): empty_first_parent 1, addition_only 16, modifies 274
- Weighted credit: 263.000/341.000
- Precision: 0.518
- Recall: 0.771

## Warnings

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0115: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.
- SZZG-0140: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.

## Results

| Scenario | Status | Run | Suite | Policy | Variant | Category | Expected BICs | Actual BICs | TP | FP | Unknown | FN | Allowed FP | Predictions | Top-k | Distractor hits | Fix shape |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|
| SZZ-0005 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0006 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0012 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0014 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0015 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0021 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0028 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0044 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0047 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0050 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0053 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0070 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0076 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0078 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0079 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0080 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0081 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0083 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0084 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0085 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0086 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0087 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0088 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0089 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0090 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0091 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0092 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0093 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0094 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0095 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0096 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0098 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0099 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0100 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0101 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0102 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0103 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0104 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0105 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0107 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0108 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0109 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0110 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0111 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0112 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0113 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0114 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0115 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0116 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0117 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0118 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0119 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0121 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0122 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0123 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0124 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0125 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0127 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0128 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0129 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0130 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0132 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0133 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0134 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0136 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0137 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0142 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0146 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0154 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0155 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0156 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0158 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0159 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0160 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0166 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0168 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0169 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0170 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0171 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0172 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0173 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c0 | - | - | - | - | c0 | - | 0 | - | - | c1:addition_only |
| SZZ-0174 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0175 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0176 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0177 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0178 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2, c3 | - | c2, c3 | - | c1 | - | 2 | - | c2, c3 | c4:modifies |
| SZZ-0179 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c3 | c2, c3 | c3 | c2 | - | - | - | 2 | - | c2 | c4:modifies |
| SZZ-0180 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c0 | c0 | c0 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0181 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0182 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0183 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0184 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0185 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0186 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0187 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0188 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0189 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0190 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0191 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0192 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c2, c4 | c2, c3, c4 | c2, c4 | c3 | - | - | - | 3 | - | - | c5:modifies |
| SZZ-0193 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0194 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0195 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZ-0196 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0197 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c5 | c1, c3, c5 | c1, c5 | c3 | - | - | - | 3 | - | - | c6:modifies |
| SZZ-0198 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0199 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0200 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0201 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0202 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0203 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0204 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 3 | - | c2 | c3:modifies |
| SZZ-0205 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0206 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0207 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0208 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0209 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c0, c3, c4 | - | c0, c3, c4 | - | c1 | - | 3 | - | c3, c4 | c5:modifies |
| SZZ-0210 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c3, c4 | - | c3, c4 | - | c1 | - | 2 | - | c3, c4 | c5:modifies |
| SZZ-0211 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c4, c5 | - | c4, c5 | - | c1 | - | 2 | - | c4, c5 | c6:modifies |
| SZZ-0212 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZ-0213 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c0, c1 | c1 | c0 | - | c3 | - | 2 | - | - | c4:modifies |
| SZZ-0214 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | - | - | - | - | c1, c3 | - | 0 | - | - | c4:addition_only |
| SZZ-0215 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZ-0216 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c0, c2, c3 | c3 | c0, c2 | - | c1 | - | 3 | - | - | c4:modifies |
| SZZ-0217 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0218 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZ-0219 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c4 | c0, c2, c3, c4 | c4 | c0, c2, c3 | - | c1 | - | 4 | - | - | c5:modifies |
| SZZ-0220 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZ-0221 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c0, c1 | c1 | c0 | - | c3 | - | 2 | - | - | c4:modifies |
| SZZ-0222 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | c2 | - | c2 | - | c1, c3 | - | 1 | - | - | c4:modifies |
| SZZ-0223 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c2, c3 | c3 | c2 | - | c1 | - | 2 | - | - | c4:modifies |
| SZZ-0224 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0225 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZG-0001 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:modifies |
| SZZG-0002 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:modifies |
| SZZG-0003 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0004 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0005 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0006 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0007 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0008 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0009 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0010 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0011 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0012 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0013 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0014 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0015 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0016 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0017 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0018 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c0, c1 | c0, c1 | c0, c1 | - | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0019 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0020 | PASS | ok | advanced-scenarios | direct_only | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0021 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:modifies |
| SZZG-0022 | PASS | ok | advanced-scenarios | exact_set | direct-only | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0023 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r2 | r2 | r2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0024 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r1 | r1, r2 | r1 | r2 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0025 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0026 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c1, c2 | c2 | c1 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0027 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2, c3 | c2 | c3 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0028 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2, c3 | c2, c3 | c2, c3 | - | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0029 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0, c1, c2 | c1 | c0, c2 | - | - | - | 4 | - | - | c2:modifies, c3:modifies |
| SZZG-0030 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 4 | - | - | c2:modifies, c3:modifies |
| SZZG-0031 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0, c1 | c1 | c0 | - | - | - | 4 | - | - | c2:modifies, c3:modifies |
| SZZG-0032 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0, c1 | c1 | c0 | - | - | - | 4 | - | - | c2:modifies, c3:modifies |
| SZZG-0033 | FAIL | ok | advanced-scenarios | partial_credit | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0034 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0035 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0 | - | c0 | - | c1 | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0036 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0, c1, c3 | c1 | c0, c3 | - | - | - | 4 | - | - | c3:modifies, c4:modifies |
| SZZG-0037 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0038 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1 | c1 | c0 | - | c2 | - | 2 | - | - | c3:modifies |
| SZZG-0039 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1, c2 | c1, c2 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0040 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c2 | c2 | c0 | - | c1 | - | 2 | - | - | c3:modifies |
| SZZG-0041 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0042 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:empty_first_parent |
| SZZG-0043 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0044 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0045 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c0, c3 | c3 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0046 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0047 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c0, c3 | c3 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0048 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0049 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 4 | - | - | c2:modifies, r2:modifies |
| SZZG-0050 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 4 | - | - | c2:modifies, r2:modifies |
| SZZG-0051 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | r2:modifies |
| SZZG-0052 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | a1 | a1, c0 | a1 | c0 | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0053 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0054 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0055 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0056 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 4 | - | - | c2:modifies, r2:modifies |
| SZZG-0057 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0058 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | r2:modifies |
| SZZG-0059 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c0 | - | c0 | - | c3 | - | 1 | - | - | c4:modifies |
| SZZG-0060 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0061 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0062 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0064 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0065 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | m1, r1 | r1 | m1 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0066 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0067 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | r2:modifies |
| SZZG-0068 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0069 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r1, r2 | r1, r2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0070 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0071 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0072 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | r2 | r2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0073 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | c0, r2 | r2 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0075 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | f1 | f1 | - | - | - | - | 1 | - | - | f2:modifies |
| SZZG-0076 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r1, r2 | r1, r2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0077 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 4 | - | - | c3:modifies, c4:modifies |
| SZZG-0078 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0081 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1, r2 | r1 | c0, r2 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0082 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0083 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0084 | FAIL | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3 | c2, c3 | c3 | c2 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0085 | FAIL | ok | advanced-scenarios | exact_set | reintroduction-direct | Revert-specific reintroduction | c3 | c2, c3 | c3 | c2 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0086 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c2, c3 | c3 | c2 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0088 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c2, c3 | c3 | c2 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0089 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c0, c3, c4 | c3 | c0, c4 | - | - | - | 3 | - | - | c5:modifies |
| SZZG-0090 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c5 | c4, c5 | c5 | c4 | - | - | - | 2 | - | - | c6:modifies |
| SZZG-0091 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c3, c4 | c4 | c3 | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0093 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0094 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c1, c2 | c2 | c1 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0095 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0096 | FAIL | ok | advanced-scenarios | top_k | - | Issue, message, context, and non-local evidence | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | rank 2 (k=1) | - | c4:modifies |
| SZZG-0097 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0098 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0, c1, c2, c3 | c1 | c0, c2, c3 | - | - | - | 4 | - | - | c4:modifies |
| SZZG-0099 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0100 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0101 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c0, c2 | c2 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0102 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0, c1, c2, c3 | c1 | c0, c2, c3 | - | - | - | 4 | - | - | c4:modifies |
| SZZG-0103 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0104 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0105 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0107 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0108 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0109 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c0 | c0 | c0 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0110 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0111 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0112 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0113 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0114 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0115 | PASS | ok | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | rank 2 (k=5) | - | c4:modifies |
| SZZG-0116 | PASS | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0117 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0118 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0119 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c3 | c2, c3 | c3 | c2 | - | c1 | - | 2 | - | - | c4:modifies |
| SZZG-0120 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0121 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2, r1 | c2 | c2 | - | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0122 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0123 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | c0, f1 | f1 | c0 | - | - | - | 2 | - | - | f2:modifies |
| SZZG-0124 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1, rel1 | r1 | rel1 | - | - | - | 2 | - | - | r2:modifies |
| SZZG-0125 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1, rel1 | r1 | rel1 | - | - | - | 2 | - | - | r2:modifies |
| SZZG-0126 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0127 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c4, f1 | c4 | f1 | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0128 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0129 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | q1 | c0, q1 | q1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0130 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1, c3 | c1 | c3 | - | - | - | 2 | - | - | c4:modifies |
| SZZG-0131 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | r1 | c0, r1 | r1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0132 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0133 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZG-0134 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0135 | FAIL | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0136 | FAIL | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0137 | PASS | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | c0 | c0 | c0 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0138 | PASS | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c2, c3 | c1, c2 | c1, c2 | - | - | c3 | - | 2 | - | - | c4:modifies |
| SZZG-0139 | FAIL | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | f1, m1 | c0, f1, m1 | f1, m1 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZG-0140 | PASS | ok | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | rank 1 (k=1) | c2 | c4:modifies |
| SZZG-0141 | PASS | ok | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c3, c4 | c3, c4 | c3, c4 | - | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0142 | PASS | ok | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0143 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c0, c1, r1 | c1 | c0, r1 | - | - | - | 4 | - | r1 | c3:modifies, r2:modifies |
| SZZG-0144 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2, c4 | c4 | c4 | - | - | c2 | - | 1 | - | - | c6:modifies |
| SZZG-0145 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0146 | FAIL | ok | advanced-scenarios | exact_set | full-cause | Evaluation policy variants | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0147 | FAIL | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3, c4 | c4 | c4 | - | - | c3 | - | 1 | - | - | c5:modifies |
| SZZG-0148 | FAIL | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c3, c4 | c0, c1 | c1 | c0 | - | c3, c4 | - | 2 | - | - | c5:modifies |
| SZZG-0149 | FAIL | ok | advanced-scenarios | partial_credit | - | Branch, merge, cherry-pick, backport, and release branches | c1, c3, c5 | c0, c1 | c1 | c0 | - | c3, c5 | - | 2 | - | - | c7:modifies |
| SZZG-0150 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0151 | FAIL | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c4, c5 | c5 | c5 | - | - | c4 | - | 1 | - | - | c6:modifies |
| SZZG-0152 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0153 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |

## Scenario notes

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0115: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.
- SZZG-0140: commit_level.required is missing or empty; required BICs inferred from bugs[].bug_introducing_commits (roles contributing/direct/reintroducing): c1.

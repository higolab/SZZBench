# SZZBench Evaluation Results

## Summary

- Total scenarios: 279
- PASS: 161
- FAIL: 118
- Tool errors: 0
- Missing prediction records: 0
- Predictions made on another repository: 0
- Invalid prediction records: 0
- True positives: 235
- False positives: 66
- Unknown predictions (counted as false positives): 0
- False negatives: 106
- Allowed false positives: 0
- Hard false positives: 52
- Related origin hits: 1
- Related-but-not-correct hits: 13
- Known distractor hits: 22
- Branch-level failures: 1 of 3 scenario(s) with a branch-level oracle
- Attribution failures: 3 of 9 scenario(s) with several bug-fixing commits
- Fix shapes (per BFC): empty_first_parent 1, addition_only 15, binary 1, mode_only 0, modifies 274
- Weighted credit: 235.000/341.000
- Precision: 0.781
- Recall: 0.689

## Information

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.

## Results

| Scenario | Status | Run | Suite | Policy | Variant | Category | Expected BICs | Actual BICs | TP | FP | Unknown | FN | Allowed FP | Predictions | Top-k | Distractor hits | Fix shape |
|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|
| SZZ-0005 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0006 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0012 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0014 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0015 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0021 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0028 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0044 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0047 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0050 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0053 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0070 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0076 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0078 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0079 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0080 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0081 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0083 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0084 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0085 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0086 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0087 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0088 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0089 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0090 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0091 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0092 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0093 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0094 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0095 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0096 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0098 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0099 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0100 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0101 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0102 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0103 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0104 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0105 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0107 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0108 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0109 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0110 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0111 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0112 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0113 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0114 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0115 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0116 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0117 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0118 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0119 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0121 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZ-0122 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0123 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0124 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0125 | PASS | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0127 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0128 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0129 | PASS | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0130 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0132 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0133 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0134 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0136 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0137 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0142 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0146 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0154 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0155 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0156 | PASS | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0158 | PASS | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0159 | PASS | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0160 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0166 | PASS | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0168 | PASS | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0169 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0170 | PASS | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0171 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZ-0172 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0173 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c0 | - | - | - | - | c0 | - | 0 | - | - | c1:addition_only |
| SZZ-0174 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0175 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0176 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0177 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0178 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c3 | - | c3 | - | c1 | - | 1 | - | c3 | c4:modifies |
| SZZ-0179 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZ-0180 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c0 | c0 | c0 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0181 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0182 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:addition_only |
| SZZ-0183 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0184 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0185 | PASS | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZ-0186 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | c2 | c3:modifies |
| SZZ-0187 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 3 | - | - | c3:modifies |
| SZZ-0188 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c3:modifies |
| SZZ-0189 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:modifies |
| SZZ-0190 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0191 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0192 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c2, c4 | c3, c4 | c4 | c3 | - | c2 | - | 2 | - | - | c5:modifies |
| SZZ-0193 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0194 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0195 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZ-0196 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0197 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c5 | c3, c5 | c5 | c3 | - | c1 | - | 2 | - | - | c6:modifies |
| SZZ-0198 | FAIL | ok | scenarios | exact_set | - | Multiple BICs, duplicate faults, and composite faults | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0199 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0200 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0201 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0202 | PASS | ok | scenarios | exact_set | - | Basic semantic line changes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZ-0203 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:addition_only |
| SZZ-0204 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0205 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0206 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c2 | - | c2 | - | c1 | - | 1 | - | c2 | c3:modifies |
| SZZ-0207 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0208 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZ-0209 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c4 | - | c4 | - | c1 | - | 1 | - | c4 | c5:modifies |
| SZZ-0210 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1 | c4 | - | c4 | - | c1 | - | 1 | - | c4 | c5:modifies |
| SZZ-0211 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1 | c5 | - | c5 | - | c1 | - | 1 | - | c5 | c6:modifies |
| SZZ-0212 | PASS | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c1, c3 | c1, c3 | - | - | - | - | 2 | - | - | c4:modifies |
| SZZ-0213 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c0, c1 | c1 | c0 | - | c3 | - | 2 | - | - | c4:modifies |
| SZZ-0214 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | - | - | - | - | c1, c3 | - | 0 | - | - | c4:addition_only |
| SZZ-0215 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c2, c3 | c3 | c2 | - | c1 | - | 2 | - | - | c4:modifies |
| SZZ-0216 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c2, c3 | c3 | c2 | - | c1 | - | 2 | - | - | c4:modifies |
| SZZ-0217 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0218 | FAIL | ok | scenarios | exact_set | - | BFC-side noise and tangled commits | c1, c3 | c1, c2, c3 | c1, c3 | c2 | - | - | - | 3 | - | - | c4:modifies |
| SZZ-0219 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c4 | c3, c4 | c4 | c3 | - | c1 | - | 2 | - | - | c5:modifies |
| SZZ-0220 | FAIL | ok | scenarios | exact_set | - | Intermediate noise and history noise | c1, c3 | c0, c1, c2, c3 | c1, c3 | c0, c2 | - | - | - | 4 | - | - | c4:modifies |
| SZZ-0221 | FAIL | ok | scenarios | exact_set | - | Basic semantic line changes | c1, c3 | c1 | c1 | - | - | c3 | - | 1 | - | - | c4:modifies |
| SZZ-0222 | FAIL | ok | scenarios | exact_set | - | Omission and deletion bugs | c1, c3 | c0 | - | c0 | - | c1, c3 | - | 1 | - | - | c4:modifies |
| SZZ-0223 | FAIL | ok | scenarios | exact_set | - | Refactoring, move, and rename after BIC | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0224 | FAIL | ok | scenarios | exact_set | - | Context, message, and non-local evidence | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZ-0225 | FAIL | ok | scenarios | exact_set | - | Non-source, configuration, test-only, and file-level edge cases | c1, c3 | c2, c3 | c3 | c2 | - | c1 | - | 2 | - | - | c4:modifies |
| SZZG-0001 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0002 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0003 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0004 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0005 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0006 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0007 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c2 | c2 | c2 | - | - | c1 | - | 2 | - | - | c3:modifies |
| SZZG-0008 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0009 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0010 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0011 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0012 | PASS | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0013 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0014 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0015 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0016 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c0, c1 | c1 | c0 | - | - | - | 2 | - | - | c2:modifies |
| SZZG-0017 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0018 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c0, c1 | c0, c1 | c0, c1 | - | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0019 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0020 | PASS | ok | advanced-scenarios | direct_only | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0021 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0022 | PASS | ok | advanced-scenarios | exact_set | direct-only | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0023 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r2 | r2 | r2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0024 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | r1 | r2 | - | r2 | - | r1 | - | 1 | - | - | c4:modifies |
| SZZG-0025 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0026 | PASS | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0027 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2 | c3 | - | c3 | - | c2 | - | 1 | - | - | c4:modifies |
| SZZG-0028 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c2, c3 | c3 | c3 | - | - | c2 | - | 1 | - | - | c4:modifies |
| SZZG-0029 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1, c2 | c1 | c2 | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0030 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0031 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0032 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0033 | PASS | ok | advanced-scenarios | partial_credit | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0034 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0035 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c0 | - | c0 | - | c1 | - | 2 | - | - | c2:modifies, c3:modifies |
| SZZG-0036 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1, c3 | c1 | c3 | - | - | - | 2 | - | - | c3:modifies, c4:modifies |
| SZZG-0037 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0038 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c0, c1 | c1 | c0 | - | c2 | - | 2 | - | - | c3:modifies |
| SZZG-0039 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c1, c2 | c1, c2 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0040 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0041 | PASS | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0042 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | - | - | - | - | c1 | - | 0 | - | - | c3:empty_first_parent |
| SZZG-0043 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0044 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0045 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0046 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | - | - | - | - | c1 | - | 0 | - | - | c4:modifies |
| SZZG-0047 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0048 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0049 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0050 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0051 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0052 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | a1 | a1 | a1 | - | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0053 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0054 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0055 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0056 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 2 | - | - | c2:modifies, r2:modifies |
| SZZG-0057 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0058 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0059 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c3 | c0 | - | c0 | - | c3 | - | 1 | - | - | c4:modifies |
| SZZG-0060 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0061 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0062 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0064 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0065 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0066 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0067 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0068 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0069 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r2 | r2 | - | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0070 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0071 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0072 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | r2 | r2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0073 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r2 | r2 | r2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0075 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | f1 | f1 | - | - | - | - | 1 | - | - | f2:modifies |
| SZZG-0076 | FAIL | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1, r2 | r2 | r2 | - | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0077 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 2 | - | - | c3:modifies, c4:modifies |
| SZZG-0078 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0081 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0082 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0083 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0084 | PASS | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0085 | PASS | ok | advanced-scenarios | exact_set | reintroduction-direct | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0086 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0088 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c3 | c3 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0089 | FAIL | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c3 | c4 | - | c4 | - | c3 | - | 1 | - | - | c5:modifies |
| SZZG-0090 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c5 | c5 | c5 | - | - | - | - | 1 | - | - | c6:modifies |
| SZZG-0091 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c4 | c4 | - | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0093 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0094 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0095 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0096 | PASS | ok | advanced-scenarios | top_k | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | - | 1 | rank 1 (k=1) | - | c4:modifies |
| SZZG-0097 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0098 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0099 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0100 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0101 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0102 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0103 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0104 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0105 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0107 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0108 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0109 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c0 | c0, c1 | c0 | c1 | - | - | - | 3 | - | - | c4:modifies |
| SZZG-0110 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0111 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0112 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0113 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0114 | PASS | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0115 | PASS | ok | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c1 | c1 | - | - | - | - | 1 | rank 1 (k=5) | - | c4:modifies |
| SZZG-0116 | PASS | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0117 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0118 | FAIL | ok | advanced-scenarios | exact_set | - | Clone, copy propagation, and origin-vs-direct BIC | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0119 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0120 | FAIL | ok | advanced-scenarios | exact_set | - | Multiple BICs, multiple BFCs, and partial fixes | c1, c2 | c2 | c2 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0121 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c2, r1 | c2 | c2 | - | - | r1 | - | 1 | - | - | c3:modifies |
| SZZG-0122 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0123 | PASS | ok | advanced-scenarios | exact_set | - | Rebase-specific history rewriting | f1 | f1 | f1 | - | - | - | - | 1 | - | - | f2:modifies |
| SZZG-0124 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0125 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | r1 | r1 | r1 | - | - | - | - | 1 | - | - | r2:modifies |
| SZZG-0126 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0127 | PASS | ok | advanced-scenarios | exact_set | - | Revert-specific reintroduction | c4 | c4 | c4 | - | - | - | - | 1 | - | - | c5:modifies |
| SZZG-0128 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1 | c1 | - | - | - | - | 1 | - | - | c4:modifies |
| SZZG-0129 | PASS | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | q1 | q1 | q1 | - | - | - | - | 1 | - | - | c2:modifies |
| SZZG-0130 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c3 | - | c3 | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0131 | PASS | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | r1 | r1 | r1 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0132 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1 | c2 | - | c2 | - | c1 | - | 1 | - | - | c3:modifies |
| SZZG-0133 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | - | - | - | - | c1 | - | 0 | - | - | c2:binary |
| SZZG-0134 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1 | c0 | - | c0 | - | c1 | - | 1 | - | - | c2:modifies |
| SZZG-0135 | FAIL | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0136 | FAIL | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | none (expect_no_bic) | c0 | - | c0 | - | - | - | 1 | - | c0 | c3:modifies |
| SZZG-0137 | PASS | ok | advanced-scenarios | exact_set | - | Evaluation policy variants | c0 | c0 | c0 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0138 | PASS | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c2, c3 | c1, c2 | c1, c2 | - | - | c3 | - | 2 | - | - | c4:modifies |
| SZZG-0139 | PASS | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | f1, m1 | f1, m1 | f1, m1 | - | - | - | - | 2 | - | - | c3:modifies |
| SZZG-0140 | FAIL | ok | advanced-scenarios | top_k | - | Evaluation policy variants | c1 | c2 | - | c2 | - | c1 | - | 1 | miss (k=1) | c2 | c4:modifies |
| SZZG-0141 | PASS | ok | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c3, c4 | c3, c4 | c3, c4 | - | - | - | - | 2 | - | - | c5:modifies |
| SZZG-0142 | PASS | ok | advanced-scenarios | exact_set | direct-only | Evaluation policy variants | c2 | c2 | c2 | - | - | - | - | 1 | - | - | c3:modifies |
| SZZG-0143 | FAIL | ok | advanced-scenarios | exact_set | - | Branch, merge, cherry-pick, backport, and release branches | c1 | c1, r1 | c1 | r1 | - | - | - | 2 | - | r1 | c3:modifies, r2:modifies |
| SZZG-0144 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c2, c4 | c4 | c4 | - | - | c2 | - | 1 | - | - | c6:modifies |
| SZZG-0145 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0146 | FAIL | ok | advanced-scenarios | exact_set | full-cause | Evaluation policy variants | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |
| SZZG-0147 | FAIL | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c3, c4 | c4 | c4 | - | - | c3 | - | 1 | - | - | c5:modifies |
| SZZG-0148 | FAIL | ok | advanced-scenarios | partial_credit | - | Evaluation policy variants | c1, c3, c4 | c1 | c1 | - | - | c3, c4 | - | 1 | - | - | c5:modifies |
| SZZG-0149 | FAIL | ok | advanced-scenarios | partial_credit | - | Branch, merge, cherry-pick, backport, and release branches | c1, c3, c5 | c1 | c1 | - | - | c3, c5 | - | 1 | - | - | c7:modifies |
| SZZG-0150 | FAIL | ok | advanced-scenarios | exact_set | - | Refactoring, move, rename, and semantic rewrite | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0151 | FAIL | ok | advanced-scenarios | reintroduction_direct | - | Revert-specific reintroduction | c4, c5 | c5 | c5 | - | - | c4 | - | 1 | - | - | c6:modifies |
| SZZG-0152 | FAIL | ok | advanced-scenarios | exact_set | - | Issue, message, context, and non-local evidence | c1, c4 | c4 | c4 | - | - | c1 | - | 1 | - | - | c5:modifies |
| SZZG-0153 | FAIL | ok | advanced-scenarios | exact_set | - | Non-source, binary, generated, and scalability edge cases | c1, c3 | c3 | c3 | - | - | c1 | - | 1 | - | - | c4:modifies |

## Scenario notes

- SZZG-0034: expected_szz also declares bug_level; these sections are not used by commit-level evaluation.
- SZZG-0097: expected_szz also declares work_item_level; these sections are not used by commit-level evaluation.
- SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by commit-level evaluation.
- SZZG-0133: expected_szz also declares line_level; these sections are not used by commit-level evaluation.

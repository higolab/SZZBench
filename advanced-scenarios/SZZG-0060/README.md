# SZZG-0060: Root cause not in changed lines

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ can identify a callee-side BIC when the BFC changes only caller-side compensation logic.

## Expected history

```text
c0: create correct range and access policy
c1: introduce boundary bug in Range.contains
c2: compensate for boundary bug in AccessPolicy
```

## Why this needs `scenario.graph.yml`

This history needs graph-aware root-cause metadata because the BFC edits `AccessPolicy.java`, while the expected BIC is the earlier
change to `Range.java`.

## Required graph-schema features

- Factors: root_cause
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether tools avoid blaming the caller line edited by the BFC when the root cause is in `Range.contains`.
- Whether context-aware analysis can connect the caller-side workaround to the callee-side boundary bug.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0060/
|-- scenario.graph.yml
`-- README.md
```

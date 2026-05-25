# SZZG-0058: Issue description required

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ can use issue text to choose the middle-name normalization BIC instead of a nearby importer cleanup commit.

## Expected history

```text
c0: create CSV contact importer
c1: introduce null handling for blank middle names
c2: change postal-code whitespace cleanup
c3: fix blank middle-name import using issue description
```

## Why this needs `scenario.graph.yml`

The code history contains more than one plausible importer cleanup, so the linked issue description is needed to identify the relevant symptom.

## Required graph-schema features

- Factors: issues, context
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether the issue description rules out the postal-code cleanup c2.
- Whether the BFC is interpreted as restoring an empty-string contract for optional middle names.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0058/
|-- scenario.graph.yml
`-- README.md
```

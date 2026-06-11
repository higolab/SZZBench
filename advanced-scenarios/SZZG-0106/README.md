# SZZG-0106: Misleading commit message with code-only BIC evidence

## Source

- Category: Context-dependent scenarios

## Purpose

Evaluate misleading commit message with code-only bic evidence and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: c0: create payment guard
c1: c1: documentation-only cleanup
c2: c2: fix zero-value payment acceptance
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: commit_message, misleading_metadata, code_evidence
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c1
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0106/
|-- scenario.graph.yml
`-- README.md
```

# SZZG-0054: Patch context required

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ can use caller context to interpret a boundary fix in the callee.

## Expected history

```text
c1: create initial state (write_file src/main/java/example/Range.java; write_file src/main/java/example/Caller.java)
c2: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: context
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether Caller.callRange provides the patch context needed to interpret Range.contains.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0054/
|-- scenario.graph.yml
`-- README.md
```

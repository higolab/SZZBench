# SZZG-0025: Bug propagates into generated code

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate Bug propagates into generated code and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: introduce origin bug (write_file templates/Range.tpl)
c1: introduce bug (write_file src/generated/java/generated/GeneratedRange.java)
c2: fix bug (replace src/generated/java/generated/GeneratedRange.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0025/
|-- scenario.graph.yml
`-- README.md
```

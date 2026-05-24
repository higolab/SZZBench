# SZZG-0008: Dependency update as BIC

## Source

- Source scenario: `FUTURE-008`
- Category: BIC property scenarios

## Purpose

Evaluate Dependency update as BIC and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create initial state (write_file pom.xml; write_file src/main/java/example/RangeAdapter.java)
c1: introduce bug (replace pom.xml)
c2: fix bug (replace src/main/java/example/RangeAdapter.java)
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
SZZG-0008/
|-- scenario.graph.yml
`-- README.md
```

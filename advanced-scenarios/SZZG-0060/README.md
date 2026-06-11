# SZZG-0060: Entity-level-only expected SZZ policy

## Source

- Category: Schema and evaluation-policy scenarios

## Purpose

Evaluate whether SZZ output can be judged against an entity-level oracle when line-level evaluation is intentionally disabled.

This is an oracle-policy scenario rather than a history-shape scenario. The faulty line is recorded for traceability, but line-level evaluation is deliberately unavailable and the expected answer is the `Range.contains` method entity.

## Expected history

```text
c1: create initial buggy range implementation (write_file src/main/java/example/Range.java)
c2: fix bug (replace src/main/java/example/Range.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: expected_szz
- Operation types: write_file, replace
- Expected SZZ policy defines line-level evaluation as unavailable and method-level entity evaluation as available.

## Evaluation points

- Whether SZZ output can be evaluated at method-entity level.
- Whether tooling respects the line_level.available=false policy.
- Whether the expected_szz entity-level oracle is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0060/
|-- scenario.graph.yml
`-- README.md
```

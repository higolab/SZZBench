# SZZG-0056: Config and code interaction

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ can identify a configuration BIC when the BFC changes code that interprets the configuration.

## Expected history

```text
c0: create retry delay config and interpreter
c1: change config unit from seconds to milliseconds
c2: document retry delay tuning
c3: make code honor the configured delay unit
```

## Why this needs `scenario.graph.yml`

The BIC is in configuration while the BFC is in code, so the scenario needs explicit context for the config/code dependency.

## Required graph-schema features

- Factors: config, code_interaction, context, faults
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the config BIC.
- Whether the code-only BFC is connected back to the config unit change.
- Whether the unrelated documentation commit c2 is ignored.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0056/
|-- scenario.graph.yml
`-- README.md
```

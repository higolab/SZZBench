# SZZG-0059: Semantically equivalent rewrite

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether SZZ traces through a semantically equivalent rewrite and reports the earlier bug-introducing commit.

## Expected history

```text
c0: create API key validator
c1: weaken API key length requirement
c2: rewrite the buggy predicate without changing behavior
c3: fix the length requirement inside the rewritten predicate
```

## Why this needs `scenario.graph.yml`

The intermediate rewrite preserves the bug, so it needs semantic metadata to avoid treating the rewrite as the BIC.

## Required graph-schema features

- Factors: semantic_rewrite, related_but_not_correct
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether c2 is recognized as preserving the already-buggy predicate rather than introducing it.
- Whether blame can pass through the predicate rewrite to the original weakening commit.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0059/
|-- scenario.graph.yml
`-- README.md
```

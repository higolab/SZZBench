# SZZG-0008: Semantically equivalent rewrite

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `semantic-rewrite`, `related-but-not-correct` |
| oracle | `exact_set`; required `c1`; related but not correct `c2` · BFC `c3` |
| graph features | 2 fault sites; `semantic_rewrites` |
<!-- /szzbench:header -->

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

## Evaluation points

- Whether SZZ identifies c1 as the BIC.
- Whether c2 is recognized as preserving the already-buggy predicate rather than introducing it.
- Whether blame can pass through the predicate rewrite to the original weakening commit.

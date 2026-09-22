# SZZG-0020: Explicit evaluation of direct BIC vs origin BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `evaluation-variant`, `direct-bic`, `origin-bic` |
| oracle | default: `direct_only`; required `c2`; related origins `c1` · `direct-only`: `direct_only`; required `c2` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · BFC `c3` |
| graph features | operation `copy_file`; 2 BICs; policy `direct_only`; 2 evaluation variants (`direct-only`, `origin-aware`); `clone_relationships` |
<!-- /szzbench:header -->

## Purpose

Evaluate direct-BIC versus origin-BIC accounting for copied buggy code.

## Expected history

```text
c0: create correct original range implementation
c1: introduce bug in original Range
c2: copy buggy Range into CopiedRange
c3: fix CopiedRange only
```

## Why this needs `scenario.graph.yml`

Direct and origin BIC roles require graph-aware bug metadata and evaluation policy.

## Evaluation points

- Whether SZZ identifies c2 as the direct BIC for `CopiedRange`.
- Whether c1 is tracked as the origin BIC without being required under direct-only scoring.
- Whether evaluation variants can distinguish direct-only and origin-aware policies.

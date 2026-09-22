# SZZG-0116: Entity-level-only expected SZZ policy

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `evaluation-variant` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | `entity_level` oracle |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ output can be judged against an entity-level oracle when line-level evaluation is intentionally disabled.

This is an oracle-policy scenario rather than a history-shape scenario. The faulty line is recorded for traceability, but line-level evaluation is deliberately unavailable and the expected answer is the `Range.contains` method entity.

## Expected history

```text
c1: create initial buggy range implementation (write_file src/main/java/example/Range.java)
c2: fix bug (replace src/main/java/example/Range.java)
```

## Evaluation points

- Whether SZZ output can be evaluated at method-entity level.
- Whether tooling respects the line_level.available=false policy.
- Whether the expected_szz entity-level oracle is applied correctly.

# SZZG-0062: File deletion

## Source

- Category: Robustness and implementation-quality scenarios

## Purpose

Evaluate a deletion-based fix where `c0` creates a buggy file and `c1` fixes the bug by deleting that file.

The required BIC is `c0`, because the initial commit introduced both `Buggy.java` and the faulty return statement.

## Expected history

```text
c0: create initial buggy file (write_file src/main/java/example/Buggy.java)
c1: fix bug (delete_file src/main/java/example/Buggy.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: delete_file
- Operation types: write_file, delete_file
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `c0` as the BIC for the deleted buggy file.
- Whether SZZ handles file deletion as the complete fix.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0062/
|-- scenario.graph.yml
`-- README.md
```

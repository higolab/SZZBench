# SZZG-0014: Buggy code copied to a new file

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate a copy-propagated bug where `c1` copies already faulty logic from `A.java` into `B.java`.

For the later fix in `B.java`, the expected direct BIC is the copy commit `c1`. The initial commit `c0` is origin context, not the required direct answer.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/A.java)
c1: copy buggy code to B.java (copy_file src/main/java/example/A.java -> src/main/java/example/B.java)
c2: fix bug (replace src/main/java/example/B.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: copy_file
- Operation types: write_file, copy_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `c1` as the direct BIC for `B.java`.
- Whether SZZ keeps `c0` as origin context without replacing the direct copy commit.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0014/
|-- scenario.graph.yml
`-- README.md
```

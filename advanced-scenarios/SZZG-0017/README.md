# SZZG-0017: Buggy code copied while original is fixed later

## Source

- Category: Copy, clone, and propagation scenarios

## Purpose

Evaluate a copied-bug scenario where `c1` copies faulty logic from `A.java` into `B.java`, `c2` fixes only the original `A.java` instance, and `c3` fixes the copied `B.java` instance.

For the `B.java` fix, the expected direct BIC is `c1`. The original faulty state in `c0` is origin context, and the original-file fix `c2` is not the BFC for the copied instance.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/A.java)
c1: copy buggy code to B.java (copy_file src/main/java/example/A.java -> src/main/java/example/B.java)
c2: fix original bug in A.java (replace src/main/java/example/A.java)
c3: fix copied bug in B.java (replace src/main/java/example/B.java)
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal scenario.yml schema.

## Required graph-schema features

- Factors: copy_file, faults
- Operation types: write_file, copy_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies `c1` as the direct BIC for the copied `B.java` instance.
- Whether SZZ does not treat the later `A.java` fix `c2` as the copied instance's BFC.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0017/
|-- scenario.graph.yml
`-- README.md
```

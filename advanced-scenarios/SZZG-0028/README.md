# SZZG-0028: The copy and the later edit are both required; the origin is not

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate whether SZZ reports the copy that carried a fault into the fixed file, and the later commit that
added a second fault to it, **without** reporting the origin the copy came from.

## Expected history

```text
c0: create amount parser
c1: introduce original parser trim bug
c2: copy amount parser to invoice parser
c3: introduce copied parser sign bug
c4: fix invoice parsing behavior
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, multiple_bic, origin_and_direct_bic
- Operation types: copy_file, replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected SZZ result

```text
Expected BIC(s): c2, c3
Related origins: c1
```

`c2` copied the untrimmed parser into `InvoiceParser.java`, the file the fix repairs, so it is that
instance's direct BIC under the [direct/origin contract](../../docs/decisions/origin-direct-contract.md) D4;
`c3` added the sign fault to the same file. `c1` removed the trim from the *source* parser and never touched
the fixed file, so it is the origin (D2): reporting it is a false positive under the default variant and is
accepted with credit 0.5 under `origin-aware`.

## Evaluation points

- Whether the copy commit `c2` rather than the origin `c1` is reported.
- Whether the second, directly written fault `c3` is reported alongside it.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0028/
|-- scenario.graph.yml
`-- README.md
```

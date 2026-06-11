# SZZG-0013: Partial credit when only some BICs are returned

## Source

- Category: Multiple BIC and BFC scenarios

## Purpose

Evaluate scoring behavior when a complete answer contains two BICs but an SZZ implementation returns only one of them.

## Expected history

```text
c0: create checkout policy classes
c1: introduce loyalty-discount threshold bug
c2: introduce tax-exemption logic bug
c3: fix both checkout policy faults
```

## Why this needs `scenario.graph.yml`

This scenario needs graph-aware expected-SZZ metadata because the oracle allows partial credit for returning only one of the two required BICs.

## Required graph-schema features

- Factors: multiple_bic, partial_credit, expected_szz
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ can identify both checkout-policy BICs for one bug.
- Whether returning only c1 or only c2 receives partial credit rather than full exact-set credit.
- Whether the BFC that edits two files is evaluated against both required BICs.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0013/
|-- scenario.graph.yml
`-- README.md
```

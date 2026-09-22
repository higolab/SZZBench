# SZZG-0033: Partial credit when only some BICs are returned

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `multi-bic`, `partial-credit`, `evaluation-variant` |
| oracle | `partial_credit`; required `c1`, `c2`; minimum 1 · BFC `c3` |
| graph features | 2 BICs; 2 fault sites; policy `partial_credit` |
<!-- /szzbench:header -->

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

## Evaluation points

- Whether SZZ can identify both checkout-policy BICs for one bug.
- Whether returning only c1 or only c2 receives partial credit rather than full exact-set credit.
- Whether the BFC that edits two files is evaluated against both required BICs.

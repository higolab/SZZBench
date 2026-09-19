# SZZG-0101: Caller/callee interaction bug

## Source

- Category: Context-aware and LLM-based SZZ scenarios

## Purpose

Evaluate whether context-aware SZZ can distinguish a valid callee behavior change from the caller commit that mishandled that behavior.

## Expected history

```text
c0: create account directory and welcome mailer
c1: allow the callee to return an empty guest name
c2: introduce caller bug by assuming the callee always returns a value
c3: fix caller fallback for empty guest names
```

## Why this needs `scenario.graph.yml`

The relevant fault depends on the relationship between caller and callee rather than on an isolated changed line.

## Required graph-schema features

- Factors: caller_callee, context, faults
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c2 as the direct BIC in the caller.
- Whether c1 is treated as required context but not as the faulty commit.
- Whether the analysis can connect the BFC line to the callee contract.

---

## Files

```text
SZZG-0101/
|-- scenario.graph.yml
`-- README.md
```

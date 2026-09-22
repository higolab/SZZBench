# SZZG-0101: Caller/callee interaction bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `caller-callee`, `context`, `api-misuse` |
| oracle | `exact_set`; required `c2`; related but not correct `c1` · BFC `c3` |
| graph features | `context` |
<!-- /szzbench:header -->

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

## Evaluation points

- Whether SZZ identifies c2 as the direct BIC in the caller.
- Whether c1 is treated as required context but not as the faulty commit.
- Whether the analysis can connect the BFC line to the callee contract.

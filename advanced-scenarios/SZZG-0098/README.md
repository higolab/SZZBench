# SZZG-0098: Only commit message provides the clue

## Source

- Category: Work-item and commit-series scenarios

## Purpose

Evaluate whether a context-aware SZZ method can use commit-message evidence when the changed code itself contains only a generic boolean gate.

## Expected history

```text
c0: create regional checkout challenge gate
c1: disable the EU checkout challenge with the only explicit message clue
c2: change an unrelated Canada rollout gate
c3: restore the EU checkout challenge
```

## Why this needs `scenario.graph.yml`

The scenario needs commit-message context because the relevant domain clue is not carried by the edited line alone.

## Required graph-schema features

- Factors: context, commit_messages
- Operation types: write_file, replace
- Expected SZZ policy is defined in expected_szz.

## Evaluation points

- Whether SZZ identifies c1 as the BIC using the PAY-314 EU clue in the commit message.
- Whether the unrelated Canada gate change c2 is not selected just because it is nearby and similar.
- Whether the BFC can be linked to the correct regional intent without relying only on line text.

---

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0098/
|-- scenario.graph.yml
`-- README.md
```

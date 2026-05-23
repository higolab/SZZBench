# SZZG-0046: work item 内に複数候補BIC

## Source

- Source scenario: `FUTURE-046`
- Category: work item / commit series 系未対応シナリオ

## Purpose

同一 work item 内に複数の BIC 候補があり、ranking が必要なケースを評価する。

## Expected history

```text
WI-001:
  c1: add feature
  c2: change validation
  c3: change caller
c4: fix
```

## Why this needs `scenario.graph.yml`

work item と ranking expectation を表現できない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    evaluation_policy: "ranking"
    preferred_order:
      - "c2"
      - "c3"
```

## Evaluation points

- top-k accuracy
- ranking-based SZZ の評価
- exact match 以外の指標

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0046/
├── scenario.graph.yml
└── README.md
```

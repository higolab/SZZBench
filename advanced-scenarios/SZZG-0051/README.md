# SZZG-0051: 同一issueに無関係commitが混在

## Source

- Source scenario: `FUTURE-051`
- Category: work item / commit series 系未対応シナリオ

## Purpose

work item / issue に無関係な commit が混在するケースを評価する。

## Expected history

```text
issue #10:
  c1: true BIC
  c2: unrelated cleanup
  c3: unrelated formatting
  c4: fix
```

## Why this needs `scenario.graph.yml`

issue に含まれる commit と bug への関連度を表現できない。

## Required graph-schema features

```yaml
work_items:
  - id: "ISSUE-10"
    commits:
      - commit: "c1"
        relevance: "bug_introducing"
      - commit: "c2"
        relevance: "unrelated"
```

## Evaluation points

- issue-aware SZZ の false positive
- work item 内のノイズ
- candidate filtering の評価

---

## I. ambiguous blame / duplicate 系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0051/
├── scenario.graph.yml
└── README.md
```

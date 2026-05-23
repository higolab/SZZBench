# SZZG-0042: feature作業の途中でBIC

## Source

- Source scenario: `FUTURE-042`
- Category: work item / commit series 系未対応シナリオ

## Purpose

1つの feature work item の中の途中 commit が BIC になるケースを評価する。

## Expected history

```text
WI-001:
  c1: add API
  c2: add validation but buggy
  c3: add tests
c4: later fix
```

## Why this needs `scenario.graph.yml`

work item / issue 単位を表現できない。

## Required graph-schema features

```yaml
work_items:
  - id: "WI-001"
    commits:
      - "c1"
      - "c2"
      - "c3"
```

## Evaluation points

- work item 内の候補を使う SZZ
- commit message / issue linkage の利用
- BIC ranking の改善

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0042/
├── scenario.graph.yml
└── README.md
```

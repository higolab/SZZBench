# SZZG-0043: fixが複数commitに分かれる

## Source

- Source scenario: `FUTURE-043`
- Category: work item / commit series 系未対応シナリオ

## Purpose

修正作業が複数 commit に分かれ、単一 BFC では不十分なケースを評価する。

## Expected history

```text
c1: bug
c2: add failing test
c3: partial fix
c4: final fix
```

## Why this needs `scenario.graph.yml`

fix series を1つの単位として表現できない。

## Required graph-schema features

```yaml
fix_series:
  - id: "FIX-B001"
    commits:
      - "c2"
      - "c3"
      - "c4"
```

## Evaluation points

- test commit を BFC に含めるか
- final fix のみを BFC とするか
- fix series 全体から SZZ を行うか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0043/
├── scenario.graph.yml
└── README.md
```

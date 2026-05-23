# SZZG-0028: partial revert による再混入

## Source

- Source scenario: `FUTURE-028`
- Category: revert / reintroduce 系未対応シナリオ

## Purpose

過去の修正の一部だけを revert し、バグが再混入するケースを評価する。

## Expected history

```text
c0: 正常
c1: bug 混入
c2: bug 修正
c3: 修正の一部だけ revert し再混入
c4: 再修正
```

## Why this needs `scenario.graph.yml`

`c3` が `c2` の partial revert であることを表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c3"
    role: "revert"
    reverts:
      - commit: "c2"
        mode: "partial"
```

## Evaluation points

- c4 に対する BIC は c1 ではなく c3 とすべきか
- partial revert の検出
- revert-aware SZZ の必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0028/
├── scenario.graph.yml
└── README.md
```

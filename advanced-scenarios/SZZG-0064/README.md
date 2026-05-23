# SZZG-0064: empty commit

## Source

- Source scenario: `FUTURE-064`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

空 commit が履歴に含まれても SZZ 実装が壊れないか確認する。

## Expected history

```text
c0: 正常
c1: empty commit
c2: bug 混入
c3: fix
```

## Why this needs `scenario.graph.yml`

現状 generator は空 commit を禁止する設計。

## Required graph-schema features

```yaml
commits:
  - id: "c1"
    allow_empty: true
    operations: []
```

## Evaluation points

- empty commit を無視できるか
- commit graph 処理の robustness
- generator / verifier の扱い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0064/
├── scenario.graph.yml
└── README.md
```

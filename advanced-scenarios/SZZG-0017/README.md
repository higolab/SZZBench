# SZZG-0017: 1つのBFCが複数bugを同時修正する

## Source

- Source scenario: `FUTURE-017`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

同一 BFC に複数 bug fix が混在するケースを評価する。

## Expected history

```text
c0: 正常
c1: bug A 混入
c2: bug B 混入
c3: bug A と bug B を同時修正
```

## Why this needs `scenario.graph.yml`

複数 `bugs` は書けるが、BFC 内のどの hunk がどの bug に対応するかを厳密に紐づけにくい。

## Required graph-schema features

```yaml
fixes:
  - id: "X001"
    bug: "B001"
    commit: "c3"
    file: "..."
    statement: "..."

  - id: "X002"
    bug: "B002"
    commit: "c3"
    file: "..."
    statement: "..."
```

## Evaluation points

- BFC 内で bug ごとの起点 hunk を分離できるか
- tangled BFC の拡張ケースとして扱うか
- bug-level evaluation と commit-level evaluation の違い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0017/
├── scenario.graph.yml
└── README.md
```

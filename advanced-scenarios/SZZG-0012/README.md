# SZZG-0012: extract class after BIC

## Source

- Source scenario: `FUTURE-012`
- Category: 中間履歴に関する未対応シナリオ

## Purpose

faulty logic を含むクラスの一部が別クラスに抽出された後に修正されるケースを評価する。

## Expected history

```text
c0: Range.java に複数責務の実装
c1: Range.java に bug 混入
c2: Validation logic を RangeValidator.java に抽出
c3: RangeValidator.java で修正
```

## Why this needs `scenario.graph.yml`

複数ファイル・entity move・origin tracking が必要。  
単純な `replace` では、なぜ fault が別ファイルへ移ったのかが表現できない。

## Required graph-schema features

- `move_entity`
- `origin_entity`
- 複数 file の fault/fix location

## Evaluation points

- refactoring-aware SZZ の必要性
- entity identity の追跡
- BIC は抽出前の commit か、抽出 commit か

---

## D. multiple BIC / multiple BFC に関する未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0012/
├── scenario.graph.yml
└── README.md
```

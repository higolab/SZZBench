# SZZG-0013: 1つのBICを複数BFCで修正する

## Source

- Source scenario: `FUTURE-013`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

1つのバグ混入 commit が複数の後続修正によって段階的に修正されるケースを評価する。

## Expected history

```text
c0: 正常実装
c1: 共通処理に bug 混入
c2: case A のみ修正
c3: case B のみ修正
```

## Why this needs `scenario.graph.yml`

`bug_fixing_commit` が単数であるため、複数 BFC を持つ bug を表現できない。

## Required graph-schema features

```yaml
bug_fixing_commits:
  - commit: "c2"
    role: "partial_fix"
  - commit: "c3"
    role: "partial_fix"
```

## Evaluation points

- 各 BFC から同じ BIC に到達するか
- BFC ごとに oracle を分けるべきか
- bug 単位と fix commit 単位の評価差

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0013/
├── scenario.graph.yml
└── README.md
```

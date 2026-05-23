# SZZG-0031: BIC before merge, BFC after merge

## Source

- Source scenario: `FUTURE-031`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

feature branch 上で導入された bug が merge 後に main で修正される標準的なケースを評価する。

## Expected history

```text
feature:
  c1: bug 混入
  c2: unrelated change

main:
  c3: merge feature
  c4: fix
```

## Why this needs `scenario.graph.yml`

DAG が必要。

## Required graph-schema features

- `branch`
- `parents`
- `merge`

## Evaluation points

- BIC が main の直線履歴上にない場合の挙動
- first-parent しか見ない SZZ が失敗するか
- merge-aware SZZ の優位性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0031/
├── scenario.graph.yml
└── README.md
```

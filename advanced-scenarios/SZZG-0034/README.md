# SZZG-0034: squash merge

## Source

- Source scenario: `FUTURE-034`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

feature branch の複数 commit が squash merge され、元の個別 BIC が main に残らないケースを評価する。

## Expected history

```text
feature:
  f1: bug 混入
  f2: unrelated
main:
  c1: squash merge feature as one commit
  c2: fix
```

## Why this needs `scenario.graph.yml`

squash の元 commit と squash commit の関係を表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c1"
    role: "squash_merge"
    squashes:
      - "f1"
      - "f2"
```

## Evaluation points

- 正解 BIC は original f1 か squash commit c1 か
- 実際の main 履歴上では f1 が存在しない場合の評価
- repository-visible oracle と conceptual oracle の違い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0034/
├── scenario.graph.yml
└── README.md
```

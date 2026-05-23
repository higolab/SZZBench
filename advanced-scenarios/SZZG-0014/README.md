# SZZG-0014: 複数BFCが同じbugを段階的に完全修正する

## Source

- Source scenario: `FUTURE-014`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

partial fix と complete fix の関係を明示する。

## Expected history

```text
c0: 正常実装
c1: bug 混入
c2: 一時的回避策
c3: 根本修正
```

## Why this needs `scenario.graph.yml`

`temporary_fix` / `complete_fix` の区別ができない。

## Required graph-schema features

```yaml
bug_fixing_commits:
  - commit: "c2"
    role: "workaround"
  - commit: "c3"
    role: "complete_fix"
```

## Evaluation points

- workaround を BFC として扱うか
- root-cause fix のみを BFC とするか
- SZZ 入力の選び方

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0014/
├── scenario.graph.yml
└── README.md
```

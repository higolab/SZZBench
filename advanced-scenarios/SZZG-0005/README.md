# SZZG-0005: BFC が merge commit である

## Source

- Source scenario: `FUTURE-005`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

merge commit 上で初めてバグ修正が行われる場合を評価する。

## Expected history

```text
main:    c0 ---- c3 merge/fix
feature:    c1 bug ---- c2 change
```

## Why this needs `scenario.graph.yml`

commit DAG、branch、merge commit の親を表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c3"
    role: "bug_fixing"
    branch: "main"
    parents:
      - "c0"
      - "c2"
```

## Evaluation points

- merge commit の diff を SZZ が扱えるか
- どちらの親との差分を起点にするか
- merge commit を無視する SZZ 実装が失敗するか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0005/
├── scenario.graph.yml
└── README.md
```

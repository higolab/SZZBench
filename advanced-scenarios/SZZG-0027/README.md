# SZZG-0027: clone removal as fix

## Source

- Source scenario: `FUTURE-027`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

バグを含むコピーコードを削除することが修正になるケースを評価する。

## Expected history

```text
c0: A.java に正しい実装
c1: buggy clone B.java を追加
c2: B.java を削除して A.java を再利用
```

## Why this needs `scenario.graph.yml`

`delete_file` が必要。  
また、fix.statement ではなく fix action が deletion になる。

## Required graph-schema features

```yaml
fix:
  commit: "c2"
  file: "B.java"
  fix_type: "file_deletion"
```

## Evaluation points

- BFC が削除のみの場合の SZZ
- 削除されたコードの BIC を追えるか
- file deletion fix の oracle 表現

---

## F. revert / reintroduce 系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0027/
├── scenario.graph.yml
└── README.md
```

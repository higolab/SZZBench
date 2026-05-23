# SZZG-0010: file move between BIC and BFC

## Source

- Source scenario: `FUTURE-010`
- Category: 中間履歴に関する未対応シナリオ

## Purpose

ファイルが別ディレクトリへ移動された後に修正されるケースを評価する。

## Expected history

```text
c0: example/Range.java 正常実装
c1: example/Range.java に bug 混入
c2: domain/Range.java へ移動
c3: domain/Range.java で修正
```

## Why this needs `scenario.graph.yml`

path 移動を semantic operation として表せない。

## Required graph-schema features

`move_file` または `rename_file` による path 変更。

## Evaluation points

- directory move を rename と同様に追跡できるか
- path-sensitive SZZ の挙動
- file identity をどう扱うか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0010/
├── scenario.graph.yml
└── README.md
```

# SZZG-0062: file deletion

## Source

- Source scenario: `FUTURE-062`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

ファイル削除が修正になる、または削除ファイルの blame が必要になるケースを評価する。

## Expected history

```text
c0: buggy file を導入
c1: bug を含むファイルを削除して修正
```

## Why this needs `scenario.graph.yml`

`delete_file` が正式 operation として未対応。

## Required graph-schema features

```yaml
- type: "delete_file"
  path: "src/main/java/example/Buggy.java"
```

## Evaluation points

- file deletion BFC
- 削除されたファイルの履歴追跡
- SZZ 実装の robustness

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0062/
├── scenario.graph.yml
└── README.md
```

# SZZG-0063: file creation only as fix

## Source

- Source scenario: `FUTURE-063`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

新しいファイルの追加のみで bug が修正されるケースを評価する。

## Expected history

```text
c0: caller expects plugin class
c1: plugin class missing
c2: missing plugin class を追加
```

## Why this needs `scenario.graph.yml`

omission bug として書けるが、fix が file creation であることを明示できない。

## Required graph-schema features

```yaml
fix:
  fix_type: "file_creation"
  file: "src/main/java/example/Plugin.java"
```

## Evaluation points

- line addition より大きい omission fix
- deleted-line-based SZZ の失敗
- file-level oracle

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0063/
├── scenario.graph.yml
└── README.md
```

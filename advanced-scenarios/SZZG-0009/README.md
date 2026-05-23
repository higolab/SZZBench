# SZZG-0009: file rename between BIC and BFC

## Source

- Source scenario: `FUTURE-009`
- Category: 中間履歴に関する未対応シナリオ

## Purpose

BIC と BFC の間でファイル名が変わるケースを評価する。

## Expected history

```text
c0: OldRange.java 正常実装
c1: OldRange.java に bug 混入
c2: OldRange.java -> Range.java に rename
c3: Range.java で bug 修正
```

## Why this needs `scenario.graph.yml`

`rename_file` がないため、Git 履歴上の rename として生成できない。

## Required graph-schema features

```yaml
- type: "rename_file"
  from: "src/main/java/example/OldRange.java"
  to: "src/main/java/example/Range.java"
```

## Evaluation points

- rename をまたいで BIC に到達できるか
- `git blame --follow` 相当が必要か
- rename commit を BIC と誤認しないか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0009/
├── scenario.graph.yml
└── README.md
```

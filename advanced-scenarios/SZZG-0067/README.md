# SZZG-0067: huge file

## Source

- Source scenario: `FUTURE-067`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

巨大ファイルを含む場合の SZZ 実装の性能・メモリ使用量を評価する。

## Expected history

```text
c0: 1万行以上のファイル
c1: 1行 bug 混入
c2: fix
```

## Why this needs `scenario.graph.yml`

表現自体は可能だが、巨大 content を `scenario.yml` に直接埋め込むのは非現実的。

## Required graph-schema features

```yaml
- type: "write_generated_text_file"
  path: "src/main/java/example/Large.java"
  lines: 10000
  template: "..."
```

## Evaluation points

- scalability
- large file diff
- blame performance

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0067/
├── scenario.graph.yml
└── README.md
```

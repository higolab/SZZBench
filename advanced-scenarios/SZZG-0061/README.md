# SZZG-0061: binary file変更

## Source

- Source scenario: `FUTURE-061`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

バイナリファイル変更を含むリポジトリで SZZ 実装が落ちないか確認する。

## Expected history

```text
c0: code + binary asset
c1: code bug
c2: code fix + binary asset update
```

## Why this needs `scenario.graph.yml`

`write_file` はテキスト前提であり、binary file を表現できない。

## Required graph-schema features

```yaml
- type: "write_binary_file"
  path: "assets/data.bin"
  content_base64: "..."
```

## Evaluation points

- binary diff を無視できるか
- 実装がクラッシュしないか
- non-text file handling

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0061/
├── scenario.graph.yml
└── README.md
```

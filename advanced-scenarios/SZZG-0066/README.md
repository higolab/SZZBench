# SZZG-0066: non-UTF-8 file

## Source

- Source scenario: `FUTURE-066`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

非UTF-8ファイルを含むリポジトリで SZZ 実装が落ちないか確認する。

## Expected history

```text
c0: Shift-JIS の設定ファイルを追加
c1: code bug
c2: fix
```

## Why this needs `scenario.graph.yml`

`write_file` は UTF-8 テキスト前提。

## Required graph-schema features

```yaml
- type: "write_file"
  path: "config/messages.properties"
  encoding: "Shift_JIS"
  content: "..."
```

## Evaluation points

- encoding handling
- tool robustness
- non-code file の扱い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0066/
├── scenario.graph.yml
└── README.md
```

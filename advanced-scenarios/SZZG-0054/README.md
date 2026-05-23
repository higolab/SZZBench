# SZZG-0054: patch context が必要

## Source

- Source scenario: `FUTURE-054`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

変更行だけでは原因を判断できず、周辺文脈が必要なケースを評価する。

## Expected history

```text
c1: caller/callee の前提を崩す変更
c2: fix は別行で guard を追加
```

## Why this needs `scenario.graph.yml`

changed line 以外の context lines を評価対象として明示できない。

## Required graph-schema features

```yaml
context:
  required_files:
    - "src/main/java/example/Caller.java"
  required_entities:
    - type: "method"
      name: "callNormalize"
```

## Evaluation points

- line-based SZZ の限界
- patch context を使う LLM-SZZ
- 周辺コードを評価に含める必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0054/
├── scenario.graph.yml
└── README.md
```

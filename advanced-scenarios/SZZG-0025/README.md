# SZZG-0025: generated code にバグがコピーされる

## Source

- Source scenario: `FUTURE-025`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

生成コードにバグが伝播し、その生成コード側で修正されるケースを評価する。

## Expected history

```text
c0: source template に bug
c1: generated file を更新
c2: generated file 側で修正
```

## Why this needs `scenario.graph.yml`

generated file と source template の関係を表現できない。

## Required graph-schema features

```yaml
files:
  - path: "generated/Parser.java"
    kind: "generated"
    generated_from: "templates/Parser.tpl"
```

## Evaluation points

- generated file を評価対象に含めるか
- source template を origin BIC とするか
- generated file の commit を direct BIC とするか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0025/
├── scenario.graph.yml
└── README.md
```

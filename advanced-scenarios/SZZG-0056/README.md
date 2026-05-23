# SZZG-0056: config と code の相互作用

## Source

- Source scenario: `FUTURE-056`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

設定変更とコード変更の組合せによりバグが発生するケースを評価する。

## Expected history

```text
c1: config で feature flag を有効化
c2: code がその設定に未対応
c3: code fix
```

## Why this needs `scenario.graph.yml`

config file と code file の interaction を明示できない。

## Required graph-schema features

```yaml
faults:
  - kind: "config"
    file: "config.yml"
  - kind: "code"
    file: "Feature.java"
```

## Evaluation points

- non-code BIC
- cross-file SZZ
- context-aware SZZ

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0056/
├── scenario.graph.yml
└── README.md
```

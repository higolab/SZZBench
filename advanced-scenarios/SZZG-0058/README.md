# SZZG-0058: issue description が必要

## Source

- Source scenario: `FUTURE-058`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

issue description がなければ BIC 候補を絞れないケースを評価する。

## Expected history

```text
c1: ambiguous code change
c2: similar code change
c3: fix
issue description: "Null input to normalize should return empty string"
```

## Why this needs `scenario.graph.yml`

外部 issue 情報を保持する場所がない。

## Required graph-schema features

```yaml
issues:
  - id: "ISSUE-1"
    title: "Normalizer fails on null"
    description: "..."
    linked_bugs:
      - "B001"
```

## Evaluation points

- issue-aware SZZ
- natural language context
- LLM-based SZZ

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0058/
├── scenario.graph.yml
└── README.md
```

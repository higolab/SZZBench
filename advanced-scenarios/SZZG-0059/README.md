# SZZG-0059: semantically equivalent rewrite

## Source

- Source scenario: `FUTURE-059`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

中間 commit が意味的には同じだが構文上大きく異なる rewrite を行うケースを評価する。

## Expected history

```text
c1: bug introduced
c2: semantically equivalent rewrite of faulty logic
c3: fix
```

## Why this needs `scenario.graph.yml`

write/replace で表現はできるが、c2 が semantic-preserving rewrite であることを表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c2"
    role: "semantic_preserving_rewrite"
    preserves_behavior: true
```

## Evaluation points

- token/AST/semantic SZZ の違い
- basic blame が c2 を返す場合の解釈
- LLM-based SZZ の可能性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0059/
├── scenario.graph.yml
└── README.md
```

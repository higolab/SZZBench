# SZZG-0048: commit messageだけが手がかり

## Source

- Source scenario: `FUTURE-048`
- Category: work item / commit series 系未対応シナリオ

## Purpose

コード差分だけでは BIC の区別が難しく、commit message が重要になるケースを評価する。

## Expected history

```text
c1: "Temporarily bypass validation for legacy import"
c2: unrelated similar code change
c3: fix validation bypass
```

## Why this needs `scenario.graph.yml`

message-aware SZZ のための期待挙動を表現できない。

## Required graph-schema features

```yaml
context_requirements:
  - type: "commit_message"
    relevant_commits:
      - "c1"
```

## Evaluation points

- commit message を使う手法の評価
- code-only SZZ との比較
- semantic context の必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0048/
├── scenario.graph.yml
└── README.md
```

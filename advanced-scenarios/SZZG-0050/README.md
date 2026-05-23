# SZZG-0050: BFC message references wrong commit

## Source

- Source scenario: `FUTURE-050`
- Category: work item / commit series 系未対応シナリオ

## Purpose

developer hint が誤っている場合に、hint-aware SZZ が誤誘導されるかを評価する。

## Expected history

```text
c1: true BIC
c2: distractor
c3: fix message incorrectly references c2
```

## Why this needs `scenario.graph.yml`

hint の正誤を表現できない。

## Required graph-schema features

```yaml
developer_hints:
  - bug: "B001"
    referenced_commits:
      - "c2"
    correctness: "incorrect"
```

## Evaluation points

- noisy hint に対する頑健性
- hint と code evidence の矛盾
- LLM/context-aware SZZ の検証

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0050/
├── scenario.graph.yml
└── README.md
```

# SZZG-0044: BICとBFCが同一issueのcommit列に属する

## Source

- Source scenario: `FUTURE-044`
- Category: work item / commit series 系未対応シナリオ

## Purpose

issue / work item を利用する SZZ が、候補範囲を狭められるか評価する。

## Expected history

```text
issue #10:
  c1: initial implementation
  c2: buggy adjustment
  c3: later fix
```

## Why this needs `scenario.graph.yml`

issue linkage がない。

## Required graph-schema features

```yaml
issues:
  - id: "ISSUE-10"
    commits:
      - "c1"
      - "c2"
      - "c3"
```

## Evaluation points

- issue-aware SZZ
- work item 内候補の ranking
- commit message 依存の評価

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0044/
├── scenario.graph.yml
└── README.md
```

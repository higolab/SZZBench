# SZZG-0049: BFC message references BIC

## Source

- Source scenario: `FUTURE-049`
- Category: work item / commit series 系未対応シナリオ

## Purpose

BFC の commit message に BIC hash が明示されている developer-informed oracle 型シナリオを評価する。

## Expected history

```text
c1: bug introduced
c2: fix, message says "Fix bug introduced by c1"
```

## Why this needs `scenario.graph.yml`

message に書くことはできるが、それが hint であり正しいことを構造化できない。

## Required graph-schema features

```yaml
developer_hints:
  - bug: "B001"
    source: "commit_message"
    commit: "c2"
    referenced_commits:
      - "c1"
    correctness: "correct"
```

## Evaluation points

- developer-informed SZZ
- message hint を使う手法
- hint がある場合とない場合の性能差

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0049/
├── scenario.graph.yml
└── README.md
```

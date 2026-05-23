# SZZG-0068: huge history

## Source

- Source scenario: `FUTURE-068`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

多数の中間 commit を含む長い履歴で SZZ の性能を測る。

## Expected history

```text
c0: normal
c1: bug introduced
c2-c1000: unrelated small commits
c1001: fix
```

## Why this needs `scenario.graph.yml`

全 commit を手書きするのは現実的でない。  
synthetic commit series generator が必要。

## Required graph-schema features

```yaml
commit_generators:
  - type: "unrelated_changes"
    count: 1000
    files: 10
```

## Evaluation points

- 履歴長に対する実行時間
- candidate pruning
- scalability

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0068/
├── scenario.graph.yml
└── README.md
```

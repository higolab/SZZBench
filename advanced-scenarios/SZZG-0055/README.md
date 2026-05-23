# SZZG-0055: caller/callee 相互作用バグ

## Source

- Source scenario: `FUTURE-055`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

caller 側と callee 側の組合せで初めてバグが発生するケースを評価する。

## Expected history

```text
c1: callee が null を許容しなくなる
c2: caller が null を渡すようになる
c3: caller または callee を修正
```

## Why this needs `scenario.graph.yml`

複数 fault location と contributing BIC が必要。

## Required graph-schema features

```yaml
bug_introducing_commits:
  - commit: "c1"
    role: "contributing"
  - commit: "c2"
    role: "direct"
faults:
  - file: "Callee.java"
  - file: "Caller.java"
```

## Evaluation points

- interaction bug の SZZ
- 複数 BIC の役割
- call graph context の必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0055/
├── scenario.graph.yml
└── README.md
```

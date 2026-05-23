# SZZG-0023: clone の片方だけ修正

## Source

- Source scenario: `FUTURE-023`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

同型バグの片方だけが修正され、もう片方が残るケースを評価する。

## Expected history

```text
c0: A.java に bug
c1: B.java にコピー
c2: A.java のみ修正
c3: B.java を後で修正
```

## Why this needs `scenario.graph.yml`

複数 bug instance と clone relationship が必要。

## Required graph-schema features

```yaml
bug_instances:
  - id: "B001-A"
    file: "A.java"
  - id: "B001-B"
    file: "B.java"
```

## Evaluation points

- instance 単位の BIC/BFC 対応
- partial propagation
- 同じ root cause を共有する複数 bug instance

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0023/
├── scenario.graph.yml
└── README.md
```

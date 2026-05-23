# SZZG-0020: buggy code copied, original later fixed

## Source

- Source scenario: `FUTURE-020`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

コピー元は修正されるが、コピー先のバグが残るケースを評価する。

## Expected history

```text
c0: A.java に bug
c1: A.java を B.java にコピー
c2: A.java の bug を修正
c3: B.java の bug を修正
```

## Why this needs `scenario.graph.yml`

copy の履歴、origin/direct BIC、複数 location が必要。

## Required graph-schema features

- `copy_file`
- direct/origin BIC
- `faults: []`

## Evaluation points

- B.java の direct BIC は c1 か
- origin BIC c0 をどのように扱うか
- A.java の fix が B.java の oracle に影響しないか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0020/
├── scenario.graph.yml
└── README.md
```

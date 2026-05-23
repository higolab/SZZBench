# SZZG-0030: BIC on feature branch, BFC on main

## Source

- Source scenario: `FUTURE-030`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

BIC が feature branch 上にあり、merge 後に main で修正されるケースを評価する。

## Expected history

```text
main:    c0 -------- c3 merge ---- c4 fix
feature:      c1 bug ---- c2 change
```

## Why this needs `scenario.graph.yml`

branch と merge commit を表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c1"
    branch: "feature"
    parents:
      - "c0"
  - id: "c3"
    branch: "main"
    parents:
      - "c0"
      - "c2"
    role: "merge"
```

## Evaluation points

- BFC から feature branch の BIC に到達できるか
- merge commit をまたいだ ancestor 探索
- linear-only SZZ の限界

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0030/
├── scenario.graph.yml
└── README.md
```

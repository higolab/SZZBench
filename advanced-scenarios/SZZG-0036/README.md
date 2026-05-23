# SZZG-0036: cherry-pick BFC

## Source

- Source scenario: `FUTURE-036`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

修正 commit が複数 branch に cherry-pick されるケースを評価する。

## Expected history

```text
main:
  c1: bug
  c2: fix

release:
  r1: cherry-pick of c2
```

## Why this needs `scenario.graph.yml`

同一修正が複数 branch に存在することを表せない。

## Required graph-schema features

- branch
- cherry_pick_of
- 複数 BFC instance

## Evaluation points

- branch-specific SZZ
- BFC の original と cherry-pick の区別
- release branch の評価

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0036/
├── scenario.graph.yml
└── README.md
```

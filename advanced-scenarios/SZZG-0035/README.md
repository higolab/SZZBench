# SZZG-0035: cherry-pick BIC

## Source

- Source scenario: `FUTURE-035`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

bug-introducing commit が別 branch に cherry-pick されるケースを評価する。

## Expected history

```text
main:    c0 -- c1 bug
release: c0 -- r1 cherry-pick of c1 -- r2 fix
```

## Why this needs `scenario.graph.yml`

cherry-pick relationship を表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "r1"
    cherry_pick_of: "c1"
```

## Evaluation points

- release branch での direct BIC は r1 か original c1 か
- duplicate commit の扱い
- hash が違う同一 patch の評価

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0035/
├── scenario.graph.yml
└── README.md
```

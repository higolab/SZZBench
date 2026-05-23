# SZZG-0038: backport introduces bug

## Source

- Source scenario: `FUTURE-038`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

backport 作業自体が新たな bug を混入するケースを評価する。

## Expected history

```text
main:
  c1: fix
release:
  r1: backport fix but introduces release-specific bug
  r2: release-specific fix
```

## Why this needs `scenario.graph.yml`

backport relation と branch-specific BIC が必要。

## Required graph-schema features

- `backport_of`
- branch
- release-specific oracle

## Evaluation points

- backport commit を BIC として返せるか
- original fix と backport bug の区別
- release maintenance における SZZ

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0038/
├── scenario.graph.yml
└── README.md
```

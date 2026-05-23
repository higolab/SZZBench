# SZZG-0041: mainで修正済み、releaseで未修正

## Source

- Source scenario: `FUTURE-041`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

main と release の修正状態が異なるケースを評価する。

## Expected history

```text
main:    c1 bug -- c2 fix
release: r1 bug -- 未修正
```

## Why this needs `scenario.graph.yml`

branch ごとの bug status を表現できない。

## Required graph-schema features

```yaml
bug_instances:
  - id: "B001-main"
    branch: "main"
    status: "fixed"
  - id: "B001-release"
    branch: "release"
    status: "open"
```

## Evaluation points

- branch ごとの BFC availability
- open bug を SZZ 評価対象にするか
- branch-aware oracle

---

## H. work item / commit series 系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0041/
├── scenario.graph.yml
└── README.md
```

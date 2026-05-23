# SZZG-0032: BIC in merge commit

## Source

- Source scenario: `FUTURE-032`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

merge conflict 解消時に bug が混入するケースを評価する。

## Expected history

```text
main:    c0 ---- c2
feature:    c1
merge:              c3 conflict resolution introduces bug
fix:                c4
```

## Why this needs `scenario.graph.yml`

merge commit 自体が BIC であること、複数親を持つことを表現できない。

## Required graph-schema features

```yaml
commits:
  - id: "c3"
    role: "bug_introducing"
    parents:
      - "c2"
      - "c1"
```

## Evaluation points

- merge conflict resolution の差分を SZZ が扱えるか
- merge commit を BIC として返すか
- merge commit を除外する SZZ の弱点

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0032/
├── scenario.graph.yml
└── README.md
```

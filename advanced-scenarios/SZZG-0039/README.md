# SZZG-0039: criss-cross merge

## Source

- Source scenario: `FUTURE-039`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

複雑な merge DAG で SZZ が ancestor を正しく扱えるか評価する。

## Expected history

```text
branch A と branch B が相互に複数回 merge される
その途中で bug が混入し、後続 merge 後に修正される
```

## Why this needs `scenario.graph.yml`

複雑な commit DAG を表現できない。

## Required graph-schema features

- commit graph
- multiple parents
- branch history

## Evaluation points

- ancestor traversal の正確性
- first-parent vs full-history の違い
- merge-heavy project での SZZ

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0039/
├── scenario.graph.yml
└── README.md
```

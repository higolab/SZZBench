# SZZG-0033: BFC in merge commit

## Source

- Source scenario: `FUTURE-033`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

merge conflict 解消時に bug を修正するケースを評価する。

## Expected history

```text
main:    c0 ---- c2 bug
feature:    c1 fix candidate
merge:              c3 merge resolves bug
```

## Why this needs `scenario.graph.yml`

merge commit を BFC とする表現が必要。

## Required graph-schema features

commit graph / merge parent / merge diff。

## Evaluation points

- どの親との差分を BFC として使うか
- merge commit の修正行から BIC を追えるか
- merge commit を除外する実装の失敗

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0033/
├── scenario.graph.yml
└── README.md
```

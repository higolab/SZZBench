# SZZG-0003: BFC が partial fix である

## Source

- Source scenario: `FUTURE-003`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

1回目の BFC ではバグを完全には修正せず、後続 commit で完全修正される場合を評価する。

## Expected history

```text
c0: 正常実装
c1: バグ混入
c2: 一部の入力ケースのみ修正
c3: 残りのケースを修正
```

## Why this needs `scenario.graph.yml`

現状では `bug_fixing_commit` が単数であり、partial fix / complete fix の区別ができない。

## Required graph-schema features

```yaml
bug_fixing_commits:
  - commit: "c2"
    role: "partial_fix"
  - commit: "c3"
    role: "complete_fix"
```

## Evaluation points

- BFC をどの commit と見なすかで BIC 推定結果が変わるか
- partial fix を起点にすると BIC を過小・過大推定しないか
- 複数 BFC を入力できる SZZ 実装が有利か

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0003/
├── scenario.graph.yml
└── README.md
```

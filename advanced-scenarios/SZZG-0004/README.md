# SZZG-0004: follow-up fix が必要な BFC

## Source

- Source scenario: `FUTURE-004`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

最初の修正が不完全で、その後 follow-up fix によって実質的な修正が完了する場合を評価する。

## Expected history

```text
c0: 正常実装
c1: バグ混入
c2: 修正 commit だが一部条件で失敗
c3: follow-up fix
```

## Why this needs `scenario.graph.yml`

partial fix と同様、複数 BFC の意味関係を表現できない。  
`c2` と `c3` のどちらを BFC として評価するかを明示できない。

## Required graph-schema features

```yaml
bug_fixing_commits:
  - commit: "c2"
    role: "attempted_fix"
  - commit: "c3"
    role: "follow_up_fix"
```

## Evaluation points

- 最初の修正 commit のみを入力した場合の SZZ 結果
- follow-up fix まで含めた場合の SZZ 結果
- fix series を単位として扱う必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0004/
├── scenario.graph.yml
└── README.md
```

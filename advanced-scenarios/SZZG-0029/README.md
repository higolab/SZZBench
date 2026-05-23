# SZZG-0029: old BIC と re-BIC の両方が plausible

## Source

- Source scenario: `FUTURE-029`
- Category: revert / reintroduce 系未対応シナリオ

## Purpose

再混入ケースで、古い BIC と再混入 commit のどちらを正解とするかが曖昧なケースを扱う。

## Expected history

```text
c1: bug 混入
c2: bug 修正
c3: 修正を戻す
c4: bug 再修正
```

## Why this needs `scenario.graph.yml`

`c1` と `c3` の関係、および評価ポリシーを表現できない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    primary_target: "reintroducing"
    true_positives:
      - "c3"
    related_but_not_correct:
      - "c1"
```

## Evaluation points

- 再混入 commit を正解とするか
- root cause と direct reintroduction の区別
- 評価ポリシーの明示

---

## G. branch / merge / cherry-pick / backport 系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0029/
├── scenario.graph.yml
└── README.md
```

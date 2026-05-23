# SZZG-0026: direct BIC vs origin BIC の明示評価

## Source

- Source scenario: `FUTURE-026`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

同じ履歴に対して、direct BIC と origin BIC のどちらを正解とするかを切り替えて評価する。

## Expected history

```text
c0: origin bug
c1: buggy code copied
c2: copied bug fixed
```

## Why this needs `scenario.graph.yml`

`bug_introducing_commits` に両方を書いても役割が分からない。  
評価対象を direct / origin から選べない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    primary_target: "direct"
    true_positives:
      - "c1"
    related_origins:
      - "c0"
```

## Evaluation points

- direct を正解にする設定
- origin を正解にする設定
- SZZ の目的による oracle 定義の違い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0026/
├── scenario.graph.yml
└── README.md
```

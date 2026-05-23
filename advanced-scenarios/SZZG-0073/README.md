# SZZG-0073: benchmark variant によって評価対象を切り替えるケース

## Source

- Source scenario: `FUTURE-075`
- Category: schema / evaluation policy が必要な横断シナリオ

## Purpose

同じ履歴に対して、strict / relaxed / direct-only / origin-aware など複数評価を行う。

## Expected history

```text
copy propagation:
  c1 origin
  c2 direct
  c3 fix
```

## Why this needs `scenario.graph.yml`

1つの `expected_szz` しか持てない。

## Required graph-schema features

```yaml
evaluation_variants:
  - name: "direct-only"
    true_positives:
      - "c2"
  - name: "origin-aware"
    true_positives:
      - "c2"
    acceptable_related:
      - "c1"
```

## Evaluation points

- 評価ポリシーによる結果の違い
- benchmark paper での透明性
- 手法比較の公平性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0073/
├── scenario.graph.yml
└── README.md
```

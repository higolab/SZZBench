# SZZG-0071: acceptable false positives を明示するケース

## Source

- Source scenario: `FUTURE-073`
- Category: schema / evaluation policy が必要な横断シナリオ

## Purpose

direct BIC ではないが、関連 commit として許容したい候補を明示する。

## Expected history

```text
c1: origin bug
c2: direct copy
c3: fix
```

## Why this needs `scenario.graph.yml`

`false_positives_allowed` はあるが、許容理由や評価上の重みを表せない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    true_positives:
      - "c2"
    acceptable_related:
      - commit: "c1"
        reason: "origin_bic"
        credit: 0.5
```

## Evaluation points

- strict evaluation と relaxed evaluation
- direct/origin の重み付け
- benchmark 結果の解釈

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0071/
├── scenario.graph.yml
└── README.md
```

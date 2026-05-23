# SZZG-0016: 複数BICのうち一部だけ返した場合の partial credit

## Source

- Source scenario: `FUTURE-016`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

複数原因バグに対して、SZZ が一部の原因だけを返した場合の評価方法を検討する。

## Expected history

```text
c1: validation 削除
c2: null 入力を許す caller 変更
c3: fix
```

## Why this needs `scenario.graph.yml`

`expected_szz` に partial credit の仕様がない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    evaluation_policy: "partial_credit"
    required:
      - "c1"
      - "c2"
    minimum_required: 1
```

## Evaluation points

- exact match ではなく recall/precision で評価する必要性
- multi-BIC SZZ の出力形式

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0016/
├── scenario.graph.yml
└── README.md
```

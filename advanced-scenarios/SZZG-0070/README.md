# SZZG-0070: top-k evaluation が必要なケース

## Source

- Source scenario: `FUTURE-072`
- Category: schema / evaluation policy が必要な横断シナリオ

## Purpose

SZZ が ranking を返す場合、正解 BIC が top-k に含まれるかを評価する。

## Expected history

```text
c1: true BIC
c2: distractor
c3: distractor
c4: fix
```

## Why this needs `scenario.graph.yml`

`expected_szz` に ranking / top-k の評価ポリシーがない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    evaluation_policy: "top_k"
    k_values:
      - 1
      - 3
      - 5
    relevant:
      - "c1"
```

## Evaluation points

- top-1 / top-3 / top-5 accuracy
- ranking quality
- distractor commit の影響

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0070/
├── scenario.graph.yml
└── README.md
```

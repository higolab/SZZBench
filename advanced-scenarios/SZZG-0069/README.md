# SZZG-0069: malformed commit message

## Source

- Source scenario: `FUTURE-071`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

極端に長い commit message、非ASCII文字、制御文字などを含む場合の SZZ 実装の robustness を確認する。

## Expected history

```text
c1: bug introduced with malformed message
c2: fix
```

## Why this needs `scenario.graph.yml`

ある程度は書けるが、malformed message の種類を体系化できない。

## Required graph-schema features

```yaml
message_variants:
  - type: "non_ascii"
  - type: "very_long"
  - type: "control_chars"
```

## Evaluation points

- parser robustness
- CSV/JSON出力時の壊れ
- LLM/context-aware SZZ の入力処理

---

## L. schema / evaluation policy が必要な横断シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0069/
├── scenario.graph.yml
└── README.md
```

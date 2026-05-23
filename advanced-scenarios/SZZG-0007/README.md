# SZZG-0007: BIC が test-only commit である

## Source

- Source scenario: `FUTURE-007`
- Category: BIC の性質に関する未対応シナリオ

## Purpose

テスト変更だけが将来の failure を引き起こす、またはテスト oracle を壊す場合を扱う。

## Expected history

```text
c0: 正常な本体コードとテスト
c1: テスト oracle を誤って変更
c2: テスト oracle を修正
```

## Why this needs `scenario.graph.yml`

SZZBench は主に production code の fault / fix を前提にしている。  
test-only change を BIC として扱う評価方針が未定義。

## Required graph-schema features

```yaml
files:
  - path: "src/test/java/example/RangeTest.java"
    kind: "test"

expected_szz:
  file_scope:
    include:
      - "test"
```

## Evaluation points

- SZZ が test files を対象にするか
- test-only BIC を正解とする評価が妥当か
- defect prediction 用のラベル付けに含めるべきか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0007/
├── scenario.graph.yml
└── README.md
```

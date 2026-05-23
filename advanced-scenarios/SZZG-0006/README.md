# SZZG-0006: BFC が generated file を含む

## Source

- Source scenario: `FUTURE-006`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

修正 commit に生成ファイルの大きな差分が含まれる場合、SZZ が生成物差分を誤って起点にしないかを評価する。

## Expected history

```text
c0: source file と generated file を導入
c1: source file に bug 混入
c2: source file を修正し、同時に generated file も更新
```

## Why this needs `scenario.graph.yml`

生成ファイルであることをメタデータとして表現できない。  
SZZ の評価上、generated file を除外すべきかどうかの方針も記述できない。

## Required graph-schema features

```yaml
files:
  - path: "src/generated/Parser.java"
    kind: "generated"
    generated_from: "grammar/Parser.g4"
```

## Evaluation points

- generated file を対象から除外できるか
- generated file の blame が false positive を生むか
- source file と generated file の両方を修正した場合の評価方針

---

## B. BIC の性質に関する未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0006/
├── scenario.graph.yml
└── README.md
```

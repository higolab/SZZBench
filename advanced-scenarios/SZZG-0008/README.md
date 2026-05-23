# SZZG-0008: BIC が dependency update である

## Source

- Source scenario: `FUTURE-008`
- Category: BIC の性質に関する未対応シナリオ

## Purpose

外部ライブラリ更新により、既存コードがバグを持つようになるケースを評価する。

## Expected history

```text
c0: library v1 を利用
c1: pom.xml / build.gradle で library v2 に更新
c2: API 仕様変更に対応する修正
```

## Why this needs `scenario.graph.yml`

dependency update が BIC であることは書けるが、外部依存関係と code behavior の関係を表現できない。  
fault location がソースコード行ではなく build file の dependency line になる。

## Required graph-schema features

```yaml
fault:
  change_type: "dependency_update"
  file: "pom.xml"
  dependency:
    group: "..."
    artifact: "..."
    from: "1.0"
    to: "2.0"
```

## Evaluation points

- non-code BIC を SZZ が扱えるか
- code fix から build file の変更へ到達できるか
- context-aware / issue-aware SZZ が有利か

---

## C. 中間履歴に関する未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0008/
├── scenario.graph.yml
└── README.md
```

# SZZG-0002: BFC が file move + fix を同時に行う

## Source

- Source scenario: `FUTURE-002`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

ディレクトリ移動と修正が同時に起こる場合の SZZ の頑健性を評価する。

## Expected history

```text
c0: src/main/java/example/Range.java を導入
c1: Range.java に bug を混入
c2: Range.java を src/main/java/domain/Range.java に移動しつつ修正
```

## Why this needs `scenario.graph.yml`

file move は rename と同様に、path の変化を Git 履歴として表現する必要がある。  
単なる `write_file` / `replace` では move の意味が失われる。

## Required graph-schema features

```yaml
- type: "move_file"
  from: "src/main/java/example/Range.java"
  to: "src/main/java/domain/Range.java"
```

## Evaluation points

- path 変更をまたいだ blame ができるか
- BFC の移動操作を BIC と誤認しないか
- file-level tracking を利用する SZZ の優位性が出るか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0002/
├── scenario.graph.yml
└── README.md
```

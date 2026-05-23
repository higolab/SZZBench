# SZZG-0045: BICがBFC直前のcleanupに隠れる

## Source

- Source scenario: `FUTURE-045`
- Category: work item / commit series 系未対応シナリオ

## Purpose

BFC の直前に cleanup commit があり、blame が cleanup を指すケースを work item 文脈で評価する。

## Expected history

```text
c1: bug 混入
c2: cleanup / refactor
c3: fix
```

## Why this needs `scenario.graph.yml`

履歴自体は書けるが、c1/c2/c3 が同一 work item に属することを表現できない。

## Required graph-schema features

`work_items`。

## Evaluation points

- basic blame は c2 を返すか
- work item information により c1 を候補化できるか
- cleanup commit の扱い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0045/
├── scenario.graph.yml
└── README.md
```

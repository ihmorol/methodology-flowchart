# Spec format

A spec is one JSON file. The builder reads it, lays it out, checks it and exports it. Complete working spec: `examples/loop-and-setup-study.json`.

## Top level

```json
{
  "name": "my-plan",
  "title": "Short figure name",
  "caption": "One sentence stating what the figure shows.",
  "page": "a4-landscape",
  "writing": {"forbid_dashes": true, "banned_words": [], "max_title_words": 5},
  "elements": []
}
```

| Field | Meaning |
|---|---|
| `name` | Output file stem. Defaults to the spec file name. |
| `title` | Document title of the HTML and PDF. |
| `caption` | One-sentence claim. Shown under the HTML figure and used as the accessible description. |
| `page` | `a4-landscape` (default), `a4-portrait`, `letter-landscape`, `letter-portrait`. |
| `writing` | Text rules. Add the person's banned words if they have a style rule. |
| `elements` | Drawn in order: groups first, then shapes, then arrows and labels. |

Coordinates are pixels on the page canvas (see the style guide). x grows right, y grows down.

## Text markup

| Write | Shows |
|---|---|
| `*η*` | italic |
| `x_{i}` | subscript |
| `10^{−4}` | superscript (use the real minus sign − for negatives) |
| `\\*` (JSON-escaped) | a literal star |

Any Unicode character in the STIX font works: Greek, ∇, Σ, ≤, →, ′, ″. The builder names any character the font lacks.

## Elements

### group

```json
{"type": "group", "id": "stage1", "x": 46, "y": 24, "w": 1108, "h": 136, "tab": "1 · Case and code"}
```

A dashed phase container. `tab` is optional; it is shown in capitals on a pill at the top-left of the border.

### box

```json
{"type": "box", "id": "tests", "x": 614, "y": 46, "w": 250, "h": 76, "tone": "cyan", "number": 3,
 "title": "Software tests", "lines": ["13 tests on synthetic cases", "derivatives, signs, BCs"], "size": 12}
```

| Field | Default | Meaning |
|---|---|---|
| `id` | auto | Name used by arrow anchors. Needed for anything an arrow touches. |
| `tone` | `blue` | One of the tones in the style guide. |
| `number` | none | Badge number. Omit for failure and small result boxes. |
| `title` | | Two to five words. |
| `lines` | `[]` | Zero to two lines (three only in a box at least 92px high). |
| `size` | 12.5 | Body text size; 12 when lines are long. |
| `thick` | false | 2px border, for final results. |

### frame

A box whose body is a row of white cells. Same fields as box, plus:

```json
{"type": "frame", "id": "net", "x": 288, "y": 164, "w": 366, "h": 92, "tone": "blue", "number": 3,
 "title": "Shared network", "cell_arrows": true,
 "cells": [{"title": "scale", "line": "2*η*/*L* − 1"}, {"title": "4 tanh layers", "line": "64 units each"}]}
```

`cell_arrows` draws arrows between cells. `cell_gap` overrides the gap (22 with arrows, 14 without). Cell ids are `net/cell1`, `net/cell2` and so on.

### diamond

```json
{"type": "diamond", "id": "pass", "cx": 988, "cy": 84, "w": 200, "h": 76, "title": "All tests pass?", "lines": ["13 of 13"]}
```

Positioned by its centre. One question, at most two short detail lines.

### row

Places boxes, frames and diamonds left to right between `x0` and `x1`, centred on the row, and connects neighbours with arrows.

```json
{"type": "row", "y": 46, "h": 76, "x0": 66, "x1": 1088, "gap": 24, "connect": true, "items": [
  {"type": "box", "id": "case", "tone": "peach", "number": 1, "title": "Locked case", "lines": ["..."]},
  {"type": "box", "id": "tests", "tone": "cyan", "number": 2, "title": "Software tests", "grow": 1, "lines": ["..."]},
  {"type": "diamond", "id": "pass", "w": 200, "title": "All tests pass?"}
]}
```

Items take the same fields as their standalone type, without coordinates. Width: `w` fixes it, `grow` shares the leftover width (default 1), diamonds default to 200. An item's own `h` is centred in the row. `"no_arrow_in": true` stops the automatic arrow into that item; `"connect": false` stops all of them.

### arrow

```json
{"type": "arrow", "from": "pass.bottom", "to": "tests.bottom", "label": "NO: fix the code", "label_at": "middle"}
```

| Field | Meaning |
|---|---|
| `from`, `to` | An anchor `id.side` (`top`, `bottom`, `left`, `right`), `id.side@0.3` for a point 30% along that side, or a raw point `[x, y]`. Diamonds accept only the four plain sides. |
| `via` | Corner points `[[x, y], ...]` for a hand route. Corners within 4px of an anchor snap onto it. |
| `via_x`, `via_y` | Position of the single middle turn when the builder routes for you. |
| `style` | `solid` (default), `loop` (dashed green, for repeats), `dashed` (dashed grey, for check-only or optional). |
| `label` | Short text. YES and NO (and labels starting "NO:" or "YES:") are bold automatically. |
| `label_at` | `start` (default), `middle`, `end`, or `[x, y]`. |
| `label_side` | `above` or `below` for horizontal segments, `left` or `right` for vertical ones. |
| `label_anchor` | `start`, `middle` or `end` when `label_at` is a point. |

Automatic routes: facing sides in line give a straight arrow; top or bottom to top or bottom gives a vertical-horizontal-vertical route; left or right to left or right gives horizontal-vertical-horizontal; mixed sides give one corner. Same-side pairs (bottom to bottom) loop 20px outside.

### label

```json
{"type": "label", "text": "saved weights", "x": 64, "y": 584, "anchor": "start", "bold": true, "color": "green", "rotate": false}
```

Free text for arrows that need a label away from their segments. `y` is the text baseline. `rotate` turns it to read upward, for labels beside vertical loop lanes. `color` is `ink` (default) or `green`.

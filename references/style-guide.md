# Style guide

The style is fixed so that every figure made with this skill looks like it belongs in the same paper. The builder applies all of it; this file explains the choices so you can use them well.

## Page

| Page | Canvas (px) | Printed |
|---|---|---|
| `a4-landscape` (default) | 1200 x 848 | 297 x 210 mm |
| `a4-portrait` | 848 x 1200 | 210 x 297 mm |
| `letter-landscape` | 1200 x 927 | 11 x 8.5 in |
| `letter-portrait` | 927 x 1200 | 8.5 x 11 in |

Keep 16px or more of white page around all content (the builder rejects anything within 12px of an edge). Content should fill at least 85% of the width and 80% of the height; a small diagram floating on a big page looks unfinished.

## Typography

One family: STIX (bundled, SIL Open Font License), a Times-like serif with full Greek and mathematical symbols. Sizes are set by the builder:

| Use | Size | Weight |
|---|---|---|
| Box title | 15px | bold |
| Box body line | 12.5px (12px with `"size": 12` when a line is long) | regular |
| Cell title / cell line | 12.5px / 11.5px | bold / regular |
| Diamond question / diamond detail | 13.5px / 11.5px | bold / regular |
| Group tab | 11.5px capitals, letter-spaced | bold, white on dark green |
| Arrow label | 10.5px | regular; YES and NO bold |
| Badge number | 11.5px | bold, white |

Text is centred in boxes. Titles are sentence case ("Pick the checkpoint"), never title case or capitals. Tabs are written in sentence case in the spec and shown in capitals.

## Colour tones

Pale fills keep the page light; the stroke and badge carry the colour. Use tones by meaning, and use the same tone for the same kind of step across a figure set.

| Tone | Fill / stroke / badge | Use for |
|---|---|---|
| `peach` | #fcebe1 / #e3a98a / #b9532b | Problem setup, fixed inputs, locked cases, the starting point |
| `blue` | #e9effb / #8ea3dc / #2f4a9a | The main method or model; selection steps |
| `purple` | #f1ebfa / #a993d6 / #6b4bb3 | Calculations: errors, derivatives, analysis |
| `green` | #e3f3ea / #82c3a1 / #23735a | Training, optimisation, the step that updates something |
| `cyan` | #e4f2f7 / #86bcd0 / #2e6f8e | Reference, baseline, tests and other check-only work |
| `gray` | #f1f2f4 / #a4a9b1 / #4b5361 | Evaluation, measurement, comparisons, notes |
| `orange` | #fef1e3 / #e2a256 / #c4691b | Final results and outputs; use `"thick": true` |
| `red` | #fbe7e3 / #e2a092 / #b0443a | Failure, stop, "not good enough", unverified |

Other fixed colours: decision diamonds #fdf3c7 fill with #d8b443 stroke; group borders #3d7a58 dashed; group tabs #2f5d46; arrows and labels #3b4049; text #1f2328; loop arrows #3d7a58 dashed.

Do not invent new colours. If a figure needs more distinctions than the tones give, the figure is trying to say too much.

## Shapes

- **Box**: rounded corners (9px), 1.3px stroke, badge circle top-left when numbered. Standard height 76px for title + 2 lines; 46px for title + 1 line without a badge; 92px for wide header boxes.
- **Frame with cells**: a box whose body is a row of white sub-cells, for showing parts of one step (network layers, inputs and outputs, before/after pairs). Needs at least 86px height.
- **Diamond**: 200 to 260px wide, 72 to 104px high. One bold question of 2 to 3 words, one short detail line.
- **Group**: dashed rounded rectangle with a pill tab on its top-left. Name the phase in the tab: "1 · Case and code", "Repeat for 3 seeds", "Set up once".
- **Arrow**: 1.6px, solid dark, filled triangular head. Only horizontal and vertical runs.

## Spacing

| Gap | Value |
|---|---|
| Between boxes in a row | 24px (20 to 28) |
| Shape to group border | 20px (at least 12) |
| Group top border to first row | 22px (the tab sits on the border) |
| Between stacked groups | 36px; this is also the lane for arrows between groups |
| Between side-by-side groups | 16px (at least 16) |
| Arrow lanes inside a group | about 10px inside the border, or midway in a gap |

Even gaps matter more than any single size. If one gap differs, the eye reads it as meaning something.

## Visual checklist (do this on the PNG)

1. The main path reads left to right, then top to bottom. Nothing has to be traced back to understand the order.
2. Box numbers follow reading order.
3. Gaps between neighbouring boxes look equal; rows line up.
4. No region is crowded while another region of similar size is empty. Large empty corners mean a row could be spread or a group shortened.
5. Every arrow starts and ends on an edge, and its label sits clearly beside it.
6. Each diamond has two labelled exits and both lead somewhere visible.
7. Failure and loop paths are visible but quieter than the main path.
8. Every symbol in the figure is either common or defined in the figure.
9. Nothing is cut at the page edge and the caption claim matches what the figure shows.

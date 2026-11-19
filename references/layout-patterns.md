# Layout patterns

Three patterns cover almost every methodology figure. Each comes with coordinates for an A4 landscape page (1200 x 848) that already pass the builder's checks. Start from them and adjust; do not start from a blank page.

Contents: height budget · Pattern A stage bands · Pattern B loop plus set-up-once · Pattern C pipeline graph · Portrait pages · Arrow routing recipes

## Height budget

Plan heights before writing coordinates. On a 848px page:

```
24 (top, room for the first tab) + sum(group heights) + 36 x (groups - 1) + 16 (bottom) <= 848
```

Typical group heights:

| Group content | Height |
|---|---|
| One row of 76px boxes | 114 |
| One row plus a loop lane under it ("NO: fix" back-arrow) | 136 |
| One row plus a small 46px box stack beside it | 134 |
| Two rows of boxes | 220 |
| Two rows plus a failure box under the second row | 300 |

If the budget does not fit, merge two thin phases, cut a box, or move detail into the document. Do not shrink text or gaps below the style guide values.

## Pattern A: stage bands

For ordered phases with gates: a research method, a project plan, a release process. One full-width group per phase, stacked top to bottom. Each band flows left to right; a lane in the gap between bands carries the arrow to the next band. This is the most general pattern and the default when unsure.

Template for four bands:

| Band | Group (x, y, w, h) | Row y | Notes |
|---|---|---|---|
| 1 | 46, 24, 1108, 136 | 46 | row x0 66, x1 1088 with a 200px diamond last; NO loop under the row at y 142 |
| 2 | 46, 196, 1108, 134 | 218 | row x0 66, x1 810; two 46px result boxes stacked at x 850 (y 210 and 270) |
| 3 | 46, 366, 1108, 300 | 388 | four boxes in a row; second row at y 494 holds a diamond and a box; red stop box at y 596 |
| 4 | 46, 708, 1108, 124 | 730 | final row: test, diamond, follow-up, orange result |

Rules that make it read well:

- The tab names the phase with a number: "1 · Case and code". Keep tabs short (under about 28 characters) so arrows can drop into the band to the right of the tab.
- The connection to the next band leaves from the last element of a band, runs along the gap lane (y in the middle of the 36px gap), and drops into the first box of the next band. Drop at x of about 290 so it clears the next band's tab.
- A result that must skip a band (for example a reference used only at the end) runs down the right margin lane at x 1174, outside all groups.
- The last band ends in an orange result box. A failure path joins the result too: failures are reported, not hidden.

## Pattern B: loop plus set-up-once

For work where a loop runs several times (training runs, survey waves, experiments) while other things are prepared once, and both meet in an evaluation. Two columns over a full-width bottom.

Working example: `examples/loop-and-setup-study.json` (a churn-model study, 13 boxes, 3 diamonds).

Template:

| Element | Coordinates |
|---|---|
| Header box 1 (problem setup) | box 46, 16, 1108, 92 |
| Left group "Repeat for 3 runs" | group 46, 140, 660, 338 |
| Right group "Set up once" | group 722, 140, 432, 338 |
| Main step as frame with 4 cells | frame 76, 168, 588, 104 |
| Two steps under it | boxes 76, 296, 290, 76 and 390, 296, 274, 76 |
| Two diamonds ("All runs done?", "Budget used?") | cx 221 and 527, cy 424, w 230, h 72 |
| Right column steps | boxes 742, 168 / 264 / 360, each 392 x 72 |
| Merged answers | box 46, 496, 660, 72 (left) and 722, 496, 432, 72 (right) |
| Evaluation diamond | cx 168, cy 664, w 256, h 104 |
| Follow-up row | boxes y 624, h 80 at x 324 to 576, 600 to 860, 884 to 1154 |
| Failure and result | red box 46, 744, 254, 80; orange box 600, 744, 554, 80 |

Loop lanes: the "next step" back-arrow runs up at x 680 (between the boxes and the left group's right border); the "next run" loop runs up at x 58, dashed green, with a rotated label beside it. Both answers feed the evaluation diamond through a lane at y 592.

Use this pattern only when the work really has that shape. It is the shape of many ML training studies, which is exactly why it gets copied onto problems where it does not fit.

## Pattern C: pipeline graph

For one pass through a system: a model architecture, a data pipeline, a computation step. One large group holds the pass, a second group holds the checks that sit outside it, and an optional bottom frame compares with a previous version.

Template:

| Element | Coordinates |
|---|---|
| Header box | box 46, 16, 1108, 92 |
| Main group | group 46, 136, 1108, 432 |
| Row 1 (inputs, model frame with cells, outputs) | y 164, h 92 |
| Row 2 (calculations, fixed inputs between them) | y 296, h 72 |
| Row 3 (combined result) and a diamond at its left | y 408, h 72; diamond cx 203, cy 444 |
| Failure box | 380, 498, 300, 52 |
| Checks group with one row of four boxes | group 46, 600, 1108, 112; row y 624, h 72 |
| Comparison frame with four cells | frame 46, 732, 1108, 100 |

The update arrow from the backward step goes straight up into the model ("new weights"), closing the loop without crossing anything.

## Portrait pages

Use `a4-portrait` (848 x 1200) when the figure goes in a single-column page or a thesis. Stage bands work best: groups span x 46 to 802, rows hold 2 or 3 boxes, and you can stack 5 or 6 bands. The right margin lane moves to x 822.

## Arrow routing recipes

- **Next in a row**: `row` elements connect neighbours automatically. Use `"no_arrow_in": true` on an item that should not receive one.
- **Down to the box below**: `"from": "a.bottom", "to": "b.top"`. If the x positions differ, the builder adds a middle turn; give `via_y` to place it in a clear lane.
- **Back to an earlier box in the same row** (a "NO: try again" loop): bottom to bottom. The default lane is 20px below the lower end; leave 34px or more of group space under the row.
- **Diamond exits**: diamonds only have the four corner anchors. Use `right` for YES going forward and `bottom` for NO going down, unless the layout makes the reverse much cleaner.
- **Across groups**: give `via` points. Snap them to lanes: the gap between groups, the right margin lane, or the inner lane about 10px inside a group border. The builder snaps a via point within 4px of an anchor onto it, so you do not need exact decimals.
- **Into a box at a chosen point**: `"to": "box.top@0.9"` enters 90% of the way along the top edge. Use this to clear a tab or to keep two incoming arrows apart.
- **From a group border** (a gate between phases): give the start as a raw point on the border, `"from": [290, 330]`.
- **Labels**: `label_at` takes `start`, `middle`, `end` or `[x, y]`. If the builder says a label collides, move it with `[x, y]` to the open side of the arrow.

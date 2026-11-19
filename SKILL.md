---
name: methodology-flowchart
description: Draws clean one-page methodology, workflow and process flowcharts (A4 or Letter) in a fixed academic style. Pale numbered boxes, dashed green phase groups with pill tabs, yellow decision diamonds, labelled orthogonal arrows, serif STIX text. A bundled builder lays out rows, routes arrows and refuses to export if text overflows, shapes overlap or arrows cross shapes. Outputs vector PDF, outlined SVG, HTML and PNG. Use whenever someone wants a methodology diagram, research workflow, phase-by-phase or stage-by-stage plan, working plan figure, pipeline or architecture flowchart, experiment or study design figure, process map, or "a diagram like this one" for a paper, thesis, proposal, report or slide, even if they only say "make a flowchart of my plan" or attach an example figure to imitate.
---

# Methodology flowchart

This skill turns a plan, method or process into a one-page flowchart that reads like a figure in a good paper. The look is fixed and proven. Your job is the content: understanding what the person actually does, cutting it into the right steps, and placing those steps so the page reads at a glance.

People came to this style after rejecting long poster-like diagrams. Those had too much text, overlapping parts and a flow copied from someone else's example. Every rule below exists to prevent one of those failures.

## What you produce

One page with:

- 8 to 16 numbered boxes, each with a 2 to 4 word title and at most two short lines;
- 2 to 4 dashed phase groups with a dark green pill tab;
- 1 to 4 yellow decision diamonds, each with two labelled exits;
- arrows that run only horizontally or vertically, with short labels where meaning is not obvious;
- files `NAME.pdf` (vector, one page), `NAME.svg` (text outlined), `NAME.html` (editable, fonts embedded), `NAME-preview.png`, and the `NAME.json` spec that built them.

Full equations, long explanations and tables belong in the person's document, not in the figure. The figure points at them.

## Workflow

### 1. Understand the request before drawing

Read what the person gave you: their message, attached figures, documents and code. If they attached an example figure, copy its *style* (this skill already matches the common style) but never its *flow*. Their steps come from their problem. Reproducing an example's boxes with new labels is the most common way this task fails.

Build a step inventory. For each step, write one line: verb, object, and the key number or rule if one exists. Then mark each step:

- **once or repeated**: does it run once, per run or seed, or per item?
- **gate**: must it finish before the next phase can start?
- **decision**: is there a yes/no question with different next steps?
- **failure exit**: what happens when it fails? Failures are results and belong on the page.
- **source**: where does each number come from? Mark a value "proposed" or "trial" if the person has not fixed it.

If a step, number or decision cannot be found in the person's material, do not invent it. Leave it out, or ask one focused question when the figure would be wrong without it. See `references/content-planning.md` for the full method and the text budgets.

### 2. Pick a layout pattern

Read `references/layout-patterns.md` and pick the pattern that matches the shape of the work:

| Shape of the work | Pattern |
|---|---|
| Ordered phases with gates (plan, research method, project stages) | **A. Stage bands**: one full-width group per phase, stacked |
| A repeated loop plus things built once, merging into an evaluation | **B. Loop plus set-up-once**: two columns over a merged bottom |
| A data or computation pipeline, one pass of a system | **C. Pipeline graph**: one big group, a checks group, an optional comparison panel |

Look at `examples/*.png` once to see the target look. Use the coordinate templates in that file as the starting point. They already respect the spacing rules, so only small adjustments are needed.

### 3. Write the JSON spec

Write `NAME.json` next to where the outputs should go. The format is in `references/spec-format.md`; `examples/loop-and-setup-study.json` is a complete, working spec to copy from. Prefer `row` elements and named anchors (`"from": "tests.bottom", "to": "pass.top"`) over raw coordinates: the builder then places boxes evenly and routes the arrows itself, which removes most layout mistakes.

Keep the colours meaningful, not decorative. `references/style-guide.md` has the palette and what each tone means.

### 4. Build and fix until clean

```bash
uv run --no-project --with fonttools --with pymupdf python <skill>/scripts/build_diagram.py NAME.json --out OUTDIR
```

Without `uv`: `pip install fonttools pymupdf`, then `python <skill>/scripts/build_diagram.py ...`. Use `--check` to validate without exporting. Export needs Chrome, Chromium or Edge; set `DIAGRAM_BROWSER` if it is installed somewhere unusual.

The builder stops with a list of problems when any of these happen:

- text wider than its box, or more lines than the box height holds;
- shapes overlapping or closer than 12px, or within 12px of their group border;
- a shape cut by a group border, or overlapping a group tab;
- groups closer than 16px;
- an arrow passing through a shape or tab, a diagonal segment, or a final segment too short for its arrowhead;
- a label on a shape, on an arrow, on a group border, on another label or off the page;
- a box title over five words, an en or em dash, or a banned word from the spec.

Fix each problem in the spec: shorten text, widen a box, move a row, add a `via` route. Never edit the builder to silence a check; each one corresponds to a defect someone saw on a real figure. Warnings (for example, content filling too little of the page) are worth fixing too.

### 5. Look at the result

Open `NAME-preview.png` and review it against the visual checklist in `references/style-guide.md`. Key questions: does the main path read left to right and top to bottom without hunting? Are gaps even? Is any area crowded while another is empty? Does any arrow have to be traced by finger? Fix and rebuild. Checks prove nothing overlaps; only looking proves the page reads well.

### 6. Deliver

Give the person the PDF (for papers and print), the SVG (for editing in Inkscape or Illustrator), the PNG (for slides and chat) and the JSON spec (for later edits). In your message, state anything the figure leaves out on purpose and every value marked proposed.

## Quick rules

- One figure, one claim. The caption says that claim in one sentence.
- Titles are names: "Software tests", "Pick the checkpoint". Body lines are facts: "13 tests on synthetic cases".
- Use the person's own words for their things. Define any symbol the figure uses, or do not use it.
- Number boxes in reading order. Failure boxes and small result boxes stay unnumbered.
- Every diamond has exactly two exits, labelled YES and NO, or with short words such as "NO: fix the code".
- Loops that repeat a run are dashed green (`"style": "loop"`). Check-only or optional flows can be dashed grey (`"style": "dashed"`).
- Keep markup simple: `*x*` italic, `_{i}` subscript, `^{2}` superscript, `\*` for a literal star.

# methodology-flowchart skill

Makes one-page methodology, workflow and phase-plan flowcharts in a clean academic style, from a plain request such as "draw the methodology for my thesis from chapter3.md".

See `examples/loop-and-setup-study.png` for what the output looks like.

## Install

- **Claude Code**: `git clone https://github.com/ihmorol/methodology-flowchart ~/.claude/skills/methodology-flowchart`, or copy this folder to `~/.claude/skills/methodology-flowchart/` (personal) or `.claude/skills/methodology-flowchart/` inside a project.
- **Claude.ai / desktop app**: open the `.skill` file and click **Save skill**.

## Requirements

- Python 3.9 or newer, with `fonttools` and `pymupdf` (`uv` installs them on the fly; otherwise `pip install fonttools pymupdf`).
- Google Chrome, Chromium or Microsoft Edge, used to print the PDF. If it lives somewhere unusual, set `DIAGRAM_BROWSER=/path/to/browser`. Without a browser you still get HTML and an SVG with embedded fonts.
- Fonts are bundled (STIX, SIL Open Font License, see `assets/fonts/OFL.txt`).

## License

Code and docs: MIT, see `LICENSE`. Fonts: SIL Open Font License 1.1, see `assets/fonts/OFL.txt`.

## Use

Ask Claude for the diagram in your own words. Point it at your plan or methods text so the steps come from your work. Examples:

- "Make a methodology flowchart for my study from docs/methods.md, A4 landscape, like the attached figure."
- "Draw our release process phase by phase: code freeze, QA, staging, rollout, with the rollback path."
- "I need an architecture diagram of our data pipeline for the proposal."

You get `NAME.pdf`, `NAME.svg`, `NAME.html`, `NAME-preview.png` and `NAME.json`. To change the figure later, ask Claude to edit the JSON and rebuild, or edit it yourself and run:

```bash
uv run --no-project --with fonttools --with pymupdf python scripts/build_diagram.py NAME.json --out OUTDIR
```

## Contents

| Path | What it holds |
|---|---|
| `SKILL.md` | The workflow Claude follows |
| `scripts/build_diagram.py` | Builder: layout, arrow routing, checks, export |
| `references/` | Style guide, layout patterns, spec format, content planning |
| `examples/` | A working spec with its preview |
| `assets/fonts/` | STIX fonts and their license |

# Content planning

Most bad methodology figures fail on content, not drawing: too much text, too little information, a copied flow, or numbers nobody can trace. This file is the method for getting the content right before any coordinates exist.

## 1. Gather

Read everything the person points at: the request, attached figures, their plan or methods document, configs, code. Note their vocabulary; the figure should use their words for their things.

If they attached an example figure "to follow", separate two things:

- **Style**: fonts, colours, boxes, spacing, arrow look. This skill already provides it.
- **Flow**: which steps exist and how they connect. This must come from *their* problem.

A figure that keeps the example's flow and swaps the labels will be rejected as a copy, even if every box is relabelled. Ask yourself: if the example were about a different topic, would my figure still have this box? If yes, why?

## 2. Build the step inventory

Write every step as one line before choosing what to draw:

```
verb + object : key fact (source)
run software tests : 13 tests on synthetic cases (strategy.md s8)
train with Adam : trial rate 1e-3 to 1e-4, 20000 steps (config, proposed)
```

Then tag each step:

| Tag | Question | Becomes |
|---|---|---|
| once / repeated | Does it run once, per run, per item? | which group it sits in; a loop arrow |
| gate | Must it finish before later work starts? | phase boundary; the band order |
| decision | Is there a yes/no with different next steps? | a diamond with two labelled exits |
| failure | What happens when it fails? | a red box or a "NO:" path to the report |
| input / output | What does it consume or produce that matters? | arrow labels, a result box |
| source | Where does each number come from? | "proposed"/"trial" marking, or leave the number out |

## 3. Choose what goes on the page

Budgets that keep a page readable:

| Item | Budget |
|---|---|
| Numbered boxes | 8 to 16 |
| Diamonds | 1 to 4 |
| Groups | 2 to 4 (up to 6 on portrait) |
| Box title | 2 to 4 words, 5 at most |
| Body lines per box | 2 (1 in small boxes) |
| Characters per body line | about 35 in a 250px box, 60 in a 390px box, 140 in a full-width header |

Too much information looks like: equations, paragraphs, tables, lists of every parameter, every sub-step as its own box. Move those into the document and let the figure point to it.

Too little information looks like: boxes that only name a topic ("Training", "Evaluation") with no fact that tells the reader what happens. Each body line should carry a specific fact: a count, a rule, a threshold, a tool, a condition.

When there are more steps than boxes, merge steps that always happen together and never fail separately. Never merge a step with a decision about it; the decision is the interesting part.

## 4. Order and group

1. Put gates in order. Work that must finish first goes higher or further left.
2. Group by phase or by repetition ("Set up once", "Repeat for each seed").
3. Number boxes in reading order. Skip numbers on failure boxes and small result boxes.
4. Every path must end somewhere: a result, a report, or a loop back. A failure that just stops should still be reported.

## 5. Honesty rules

These keep the figure from making claims the work has not earned:

- Every number traces to the person's material. If it is a plan, not a fixed value, say "proposed", "trial" or "target".
- Do not add steps the person does not do, even if similar work usually has them. If an important step seems missing, ask; do not draw it in.
- Do not show a result as achieved when the figure is a plan.
- Keep failure paths visible. A plan that shows only success hides the decisions reviewers care about.
- Define every symbol the figure uses, in the box or in a header line. A symbol the reader cannot decode is noise.
- If a decision depends on something still open (a supervisor's answer, a pending choice), say it is pending in the box rather than guessing.

## 6. Write the text

- Titles are names, in sentence case: "Pick the checkpoint", "Reference checks".
- Body lines are lower-case fragments with facts: "best rank on monitor points".
- Plain words. Prefer "use" to "utilize", "check" to "validate the correctness of".
- No en or em dashes; use a colon, a comma or "to" ("10^{−5} to 10^{−7}").
- Same term for the same thing everywhere in the figure.
- The caption states the figure's one claim in one sentence.

## Worked example: how a copied flow was fixed

A researcher asked for a methodology figure and attached a figure from another project as the style to follow. The first attempt kept the attachment's flow: a training loop on the left, "set up once" on the right, an accuracy diamond, then the attachment's follow-up boxes with new labels. The researcher rejected it as a direct copy.

The fix came from the step inventory. The project's own rules said the work passes through gates: fix the inputs and pass software tests, then build a reference solution, then train, then test and report. That gave four stage bands (Pattern A) instead of the borrowed two columns. Steps specific to the problem appeared once the inventory was honest: a scaling decision driven by the problem's own numbers, an "unverified reference" branch, a stop on invalid values.

The lesson: start from the person's step inventory, then choose the pattern. Never start from the example's boxes.

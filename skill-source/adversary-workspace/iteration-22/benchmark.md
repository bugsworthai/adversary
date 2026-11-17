# Iteration 22: 2.17.0 (visual, branded HTML preview with flowcharts)

Offline runs of evals 1 and 2 with `dry run ; html`, one run each, BRANDING at its default (off).

- Banner first in both outputs, `v2.17.0 (latest)`.
- Eval 1: 11 findings, 2 finding flowcharts and 1 overview, 0 renderer warnings.
- Eval 2: 3 findings, 1 flowchart, 0 renderer warnings; convention-allowed patterns held back.
- No comment has a footer or link; the fixed sentence is on every comment; flows are only in the `flow`/`overview` fields, never in `content`.
- The page carries the AdversaryPR logo, name and version in its header and footer (checked in `preview.html`).

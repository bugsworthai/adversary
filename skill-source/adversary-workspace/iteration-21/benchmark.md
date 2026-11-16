# Iteration 21: 2.16.0 (no footer or link on comments by default)

Offline runs of evals 1 and 2, one run each, with BRANDING at its default (off).

- Banner first in both outputs, `v2.16.0 (latest)`.
- Eval 1: 11 findings, 0 placement warnings. No comment has a footer or a link to adversarypr.com, in the output or in findings.json. The fixed sentence is on all 11; none opens with `I noticed`.
- Eval 2: 3 findings, convention-allowed patterns held back. No footer or link; the fixed sentence is on all 3.
- Not tested offline: turning branding on (`branding=on`), which is covered by the instructions only.

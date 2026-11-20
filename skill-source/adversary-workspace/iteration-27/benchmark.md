# Iteration 27: version 2.22.0 (offline)

Eval 1 (`dry run ; html`, fit `overlaps`) and eval 2 (`dry run`, fit `current`), no clone, impact from the diff alone.

- Eval 1: 12 findings (P1 4, P2 4, P3 3, P4 1); impact 4/5 Wide; no renderer WARNING; the page shows the scorecard (Impact on the codebase, Fit with main).
- Eval 2: 4 findings (P1, P2, P3, P4); impact 2/5 Local; six convention-backed points held back.
- Script checks: every P1 and P2 has the fixed sentence and a fenced fix; no suggestion block; no comment mentions impact, rebase, adversarypr.com, adversarial or hostile; no "cannot", "does not", "do not", "will not" or "may not" in comment prose.
- Note from the eval 1 agent: the fixture's PR title and fit overlap file don't match the diff; the fixture is made up, so that is expected.

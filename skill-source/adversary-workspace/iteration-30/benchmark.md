# Iteration 30: version 2.25.0 (offline)

Eval 1 (`dry run ; html`, fit `behind`, run with the html maps and summary) and eval 2 (`dry run`, fit `current`, no html), no clone, impact from the diff alone.

- Eval 1: 12 findings (P1 6, P2 2, P3 3, P4 1); impact 4/5; summary and all three maps written; one renderer WARNING on the first pass (a map node title over 36 characters), fixed and rerun clean; no WARNING at the end.
- Eval 2: 3 findings (P1, P2, P4); impact 2/5; the --text step printed no WARNING; no maps or summary (no html), as intended.
- Script checks: every P1 and P2 has the fixed sentence and a fenced fix; no suggestion block; no comment mentions impact, rebase, merge status, adversarypr.com, adversarial or hostile; no stiff phrasing in comment prose (one "does not" hit was "does nothing" inside a description of code, not stiff phrasing).
- Maps in eval 1 are taken from the code (edges named real calls and the failures the findings describe). The data model map was thin (3 nodes, 1 edge).
- Known: the agent read the instructions before printing the banner, as in earlier iterations. The eval 1 agent built its data files with a helper script rather than by hand.

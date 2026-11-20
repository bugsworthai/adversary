# Iteration 25: version 2.20.0 (offline)

Evals 1 and 2, `dry run` (eval 2 also `html`), fit fixtures `overlaps` (eval 1) and `conflicts` (eval 2), no clone so impact is scored from the diff alone.

- New in 2.20.0: the `Fit:` line printed before the review and again in the `--text` output; `Impact n/5` with reasons (eval 1: 4 Wide; eval 2: 2 Local); an `overview` flowchart (11 and 7 steps) printed as text with finding badges; no comment mentions fit, impact or rebasing.
- Eval 1: 10 findings (P1 4, P2 2, P3 3, P4 1). Covers the LSP, money-in-Double, diverged shipping threshold, getter side effect, missing HTTP status check, SRP, YAGNI and flag-argument items. Every comment has the fixed sentence and a fenced fix, none uses a suggestion block.
- Eval 2: 3 findings (P1 force unwrap, P2 stale pagination hint, P4 missing test); 6 convention-backed points held back; no renderer WARNING; PDF exported.
- Known gap: the model read the instructions before printing the banner in the eval 2 run (the banner is at the top of review.md). Same behavior as earlier iterations.

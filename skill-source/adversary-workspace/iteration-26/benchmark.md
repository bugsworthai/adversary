# Iteration 26: version 2.21.0 (offline)

Evals 1 and 2, `dry run`. Fit fixtures: eval 1 `behind` with `overlapChecked: false` (GitHub capped the file list), eval 2 `current`. No clone, so impact is scored from the diff alone.

- Eval 1: 11 findings (P1 5, P2 2, P3 3, P4 1); impact 3/5 Shared; 12-step flowchart; Fit line read "1357 commits behind main; whether its files changed there was not fully checked (GitHub capped the file list at 300)".
- Eval 2: 3 findings (P1, P2, P4); impact 2/5 Local; 8-step flowchart; Fit line "Up to date with main".
- Checks run by script: every P1 and P2 comment has the fixed sentence and a fenced fix; no suggestion block; no comment mentions impact, rebase, adversarypr.com, adversarial or hostile.
- Also run on a real public PR (cli/cli#13697, dry run, html): that run found the capped-list gap that 2.21.0 fixes.

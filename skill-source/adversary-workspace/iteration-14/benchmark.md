# Iteration 14: 2.10.0 (employer names removed; bare PR number uses the current repo)

Offline runs of evals 1 and 2, one run each, graded by hand and by script.

- Banner: exact, with `v2.10.0 (latest)`, in both runs.
- Footer: `Comment by Sam using Adversary ([adversarypr.com](https://adversarypr.com))` on every comment (10 and 3).
- Format: every comment is question-led, has the fixed sentence, and a fenced fix. No retired words.
- Eval 1: 10 findings, including the planted double-read side effect, read-only playlist, Double money, undefined helpers, and the 35 vs 50 threshold. The HTTP-status check was not reported (it has been inconsistent in every version).
- Eval 2: 3 findings; the patterns the repo's CLAUDE.md allows were held back.
- Placement: render_preview.py reports 0 warnings for both.
- Not exercised offline: the new bare-number rule (needs a git remote), so it is untested beyond reading.

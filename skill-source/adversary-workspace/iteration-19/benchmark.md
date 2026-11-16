# Iteration 19: 2.14.0 (logo on every run; clickable HTML preview link; footer switch)

Offline runs of evals 1 (with `html`) and 2, one run each.

- Banner: first thing in both outputs, exact, `v2.14.0 (latest) · reviews on this session's model`. The agents had to read `SKILL.md` before printing it, because an offline agent has no preloaded skill. In real use the skill is already in context, so the first real run is the true check.
- Eval 1 with `html`: render_preview.py reports 0 warnings and prints the `file://` link, and the chat output has that link on its own line (also covered by `tools/tests/test_render_preview_link.py`).
- Footer, fixed sentence, no `I noticed`: all 8 comments in eval 1's findings.json and all 3 in eval 2.
- Eval 1: 8 findings (iteration 18 had 11). Planted bugs caught: LSP, Double money, shipping-threshold DRY, view-model SRP, hasUnreadMessages side effect, YAGNI factory, boolean flags. Missed: the HTTP status is never checked before decoding. One run, no change to the review rules in 2.14.0, so this looks like run-to-run variation, but it is worth a re-run.
- Eval 2: 3 findings, convention-allowed patterns held back.
- Not tested offline: `-nobranding` at the selection prompt (stops before the answer).

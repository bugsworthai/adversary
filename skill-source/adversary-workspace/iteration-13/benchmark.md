# Iteration 13: AdversaryPR 2.9.0 (the reviewer's own instructions reworded in a warmer tone)

Offline, one run each, Sonnet 5.5, telemetry skipped, nothing posted, no network. The change under test: "hostile / assume wrong / attack / strong opinions" wording became "careful, thorough, on the author's side / check what the code does / say it plainly". The checks, the evidence standard and the comment format are meant to be unchanged. The question is whether softer wording makes the reviewer miss things.

| Eval | Result |
|---|---|
| 1 mixed stack (ADO) | 11 findings. Every checklist item present, including the HTTP-status check (a P2). Severity order correct, 3 P3 design findings (cap 5). All new-format checks 11/11. |
| 2 conventions restraint (ADO) | 2 findings (force-unwrap P1, stale-state P2), 0 design findings, all convention-sanctioned patterns held back. 2/2 on every format check. |
| 7 GitHub PR | 10 findings. Planted bugs caught except the HTTP-status point, which this run held back as low cost (eval 7 does not grade it). 3 `suggestion` blocks, all anchored on added lines of one hunk. 10/10 on every format check. |
| 8 branding off (ADO) | 10 findings. Planted bugs caught (read-only `add()` throw, money in `Double`, the diverging shipping rule, the getter side effect, SRP, YAGNI, flag arguments, missing imports); HTTP status held back (eval 8 does not grade it). Footer exactly `Comment by sam.example` on 10/10. |

New check (added to evals 1 and 7): no comment contains adversarial, hostile, tough, or blunt. Passed on all four runs. The 15-row banner matched exactly in all four; `render_preview.py` reported no warnings on any; no `#<number>` in any comment.

Reading the result: across these four runs the softer wording did not lose any planted bug that the checklist grades. The HTTP-status point is the one that has always been inconsistent (caught in eval 1 here; dropped as low cost in evals 7 and 8, as it was in earlier versions), so it is the one to watch. One run each, so this is evidence, not proof; repeat on a few real PRs before relying on 2.9.0 for anything critical.

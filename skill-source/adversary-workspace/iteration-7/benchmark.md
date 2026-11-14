# Iteration 7: AdversaryPR 2.3.0 with the ASCII logo banners

Offline, one run each, Sonnet 5.5 for the evals, Haiku 5.5 for the banner-only check.

| Check | Result |
|---|---|
| Eval 1, mixed stack | 11 findings (5 P1, 1 P2, 4 P3, 1 P4). Traps left alone. |
| Eval 2, conventions restraint | 2 findings (P1 force unwrap, P2 stale state), 0 design findings. |
| Latest banner (15-row outline) | Reproduced exactly in both evals; row 8 carries the model suffix. |
| Older-version banner (15-row solid, `version=2.2.0`) | Reproduced exactly by Haiku; row 8 carries the model suffix. |

`render_preview.py` reported no placement warnings. Failure-scenario and tone assertions were spot-checked, not read line by line.

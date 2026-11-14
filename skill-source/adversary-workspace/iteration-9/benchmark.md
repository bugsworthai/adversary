# Iteration 9: AdversaryPR 2.5.0 (opt-in anonymous usage counts)

Offline, one run each, Sonnet 5.5, `/adversary <PR> ; dry run`. Telemetry was skipped in both runs (the offline prompt says to skip Step 0 item 6), so these runs do not exercise the consent question or the send step; that logic is covered by `tools/tests/test_telemetry.py` only.

| Eval | Result | Notes |
|---|---|---|
| 1 mixed stack | 17/17 | 9 findings (4 P1, 1 P2, 3 P3, 1 P4). The HTTP-status check is in the P2 finding (missed in iteration 8). Traps (DTOs, `HTTPMethod`, test setup) left alone. |
| 2 conventions restraint | 10/10 | 2 findings (P1 force unwrap, P2 stale state), 0 design findings, convention-sanctioned patterns held back. |

Both runs opened with the 15-row outline banner, reproduced exactly, with `AdversaryPR v2.5.0 (latest)` on the middle row. `render_preview.py` reported no placement warnings (9 and 2 findings). Neither run mentioned telemetry or usage counts.

Grading note: banner, finding presence/absence, severity order and the P3 cap were checked against the findings tables and review text. Failure-scenario and tone assertions were spot-checked, not read line by line. One run each; eval 1 findings vary run to run (iteration 8 missed one check that this run caught).

# Iteration 8: AdversaryPR 2.4.0 (command renamed to `/adversary`)

Offline, one run each, Sonnet 5.5, `/adversary <PR> ; dry run`. 2.4.0 is 2.3.0 with the command, skill name and run-folder renamed; the rules are unchanged.

| Eval | Result | Notes |
|---|---|---|
| 1 mixed stack | 16/17 | 12 findings (6 P1, 2 P2, 3 P3, 1 P4). Traps left alone. **Missed:** "flags that `ProfileViewModel.load()` never checks the HTTP response status". The agent saw it and dropped it as weak ("a bad body would fail to decode anyway"), so it is not in the review at all. Iterations 6 and 7 caught it, so this looks like single-run variance, not a rename effect; repeat before concluding. |
| 2 conventions restraint | 10/10 | 2 findings (P1 force unwrap, P2 stale state), 0 design findings, convention-sanctioned patterns left alone. `preview.md` was not written for this PR (the instructions list it); `findings.json` was. |

Both runs opened with the 15-row outline banner, reproduced exactly, with `AdversaryPR v2.4.0 (latest)` on the middle row. `render_preview.py` reported no placement warnings on eval 1 (12 findings).

Grading note: banner, finding presence/absence, and the P3 cap were checked against the findings tables and review text. Failure-scenario and tone assertions were spot-checked, not read line by line.

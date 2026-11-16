# Iteration 20: 2.15.0 (a token for each Azure DevOps organization)

Offline runs of evals 1 and 2, one run each. The credential steps (1 and 2) are skipped offline, so these runs check that the review itself is unchanged; the credential helper is covered by `tools/tests/test_creds.py` (13 tests).

- Banner first in both outputs, `v2.15.0 (latest)`.
- Eval 1: 11 findings, including the missing HTTP status check that iteration 19 missed. 0 placement warnings from render_preview.py. All 11 comments have the footer and the fixed sentence; none opens with `I noticed`.
- Eval 2: 3 findings, convention-allowed patterns held back; footer and fixed sentence on all 3.

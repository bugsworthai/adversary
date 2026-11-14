# Iteration 10: AdversaryPR 2.6.0 (GitHub PRs, comment footer, hidden branding option)

Offline, one run each, Sonnet 5.5. Telemetry skipped. No GitHub or Azure DevOps call was made, so the GitHub posting flow is untested against the real API; these runs exercise fetching-from-saved-files, review, footers and preview only.

| Eval | Result | Notes |
|---|---|---|
| 1 mixed stack (ADO, branding default) | 16/17 | 9 findings. **Missed again:** "flags that `ProfileViewModel.load()` never checks the HTTP response status" (held back as weak). Footer present on all 9. Missed in iterations 8 and 10, caught in 6, 7 and 9. |
| 2 conventions restraint (ADO) | 10/10 | 2 findings, 0 design findings, restraint intact. Footer on both. |
| 7 GitHub PR (new) | 8/8 | Provider github, folder `PR-gh-orders-api-101`, 12 findings, no leading slash on any path, footer `Comment by sam-example using Adversary (adversarypr.com)` on all 12, no `#<number>`, nothing posted, no token. |
| 8 branding off (new) | 11/11 | 11 findings, footer exactly `Comment by sam.example` on all, no "Adversary" or adversarypr.com in any comment, the output never mentions the option. |

Checked mechanically: the 15-row outline banner matched exactly in all four runs with `AdversaryPR v2.6.0 (latest)`; every finding's content ends with `"\n\n" + footer` exactly once; GitHub paths have 0 leading slashes (ADO: all have one); `render_preview.py` reported no warnings on any run, and its GitHub page says GitHub (no Azure DevOps wording) and carries the footer on all comments; the branding-off preview has no "using Adversary".

Grading note: failure-scenario and tone assertions were spot-checked, not read line by line. One run each. The only word "branding" in eval 8's review.md is the test folder name in the RUN_DIR line.

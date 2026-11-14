# Iteration 11: AdversaryPR 2.7.0 (question-led comments with code snippets; GitHub suggested changes)

Offline, one run each, Sonnet 5.5, telemetry skipped. Nothing was posted and no GitHub or Azure DevOps call was made, so GitHub's own "Commit suggestion" button was never exercised against a real PR; these runs show what the skill would send.

| Eval | Original checklist | New-format checks |
|---|---|---|
| 1 mixed stack (ADO) | 17/17 (HTTP-status check caught, as a P2) | 12 findings: question 12/12, standard sentence 12/12, fenced fix 12/12, no `suggestion` block, footer exact 12/12 |
| 2 conventions restraint (ADO) | 10/10 | 2 findings: all four checks 2/2 |
| 7 GitHub PR | 8/8 | 10 findings: question 10/10, fenced fix 10/10, sentence 9/10 (the P4 test-gap comment says "suggested skeleton" instead; the rule covers P1/P2). 3 `suggestion` blocks, each verified to replace exactly its anchored lines (11-12, 33-37, 25), flags agree with content |
| 8 branding off (ADO) | 11/11 | 12 findings: all four checks 12/12, footer exactly `Comment by sam.example` |

Mechanical checks: the 15-row banner matched exactly in all four runs; no `#<number>` in any comment; Azure DevOps paths all have a leading slash and GitHub paths none; `render_preview.py` reported no placement warnings on any run; no `suggestion` block on any Azure DevOps PR.

Grading notes: whether each question is "genuine" rather than rhetorical, and tone, were spot-checked by reading samples, not every comment. One run each. A first check of the suggestion anchors by hand was wrong (it skipped blank context lines); the recount above is the correct one.

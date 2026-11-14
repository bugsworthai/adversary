# Iteration 12: AdversaryPR 2.8.0 (the signature's address is a link)

Offline, one run each (evals 1 and 7 only), Sonnet 5.5, telemetry skipped. Nothing was posted and no network call was made.

| Eval | Result |
|---|---|
| 1 mixed stack (ADO) | 13 findings. Linked footer exact on 13/13, one per comment. Question, standard sentence and fenced fix on 13/13. No `suggestion` block. All paths have a leading slash. The HTTP-status check was caught (a P1). |
| 7 GitHub PR | 9 findings. Linked footer exact on 9/9. Question, sentence and fenced fix on 9/9. 2 `suggestion` blocks, both anchored on added lines of one hunk, flags agree with content. No leading slash on any path. |

Mechanical checks: the 15-row banner matched exactly in both; no `#<number>` in any comment; no old unlinked footer left; `render_preview.py` reported no warnings on either run and the GitHub preview page carries a real link to https://adversarypr.com on all 9 comments.

Not run this iteration: evals 2 and 8 (the footer change does not touch what they grade; eval 8's branding-off footer is unchanged). Grading notes: whether each question is "genuine" was spot-checked, not read line by line. One run each. The GitHub run's finding 4 has one awkward phrase ("a total of unknown content"); it was left as written.

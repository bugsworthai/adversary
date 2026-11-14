# SnipDragon 2.0.0: model comparison (2026-11-11)

Same skill (`version=2.0.0`) and the same offline inputs and checklists as iteration-2, with one run per model per test. Opus 5.5 numbers come from iteration-2.

| Model | Mixed PR (17 checks) | Restraint PR (10 checks) | Comment lines that land on the diff | Wrote findings.json | Time (mixed / restraint) | Tokens (mixed / restraint) |
|---|---|---|---|---|---|---|
| Opus 5.5 | 17/17 | 10/10 | 17/17 | yes, both | 10.2 min / 5.5 min | 171k / 131k |
| Sonnet 5.5 | 17/17 | 10/10 | 13/13 (restraint run not checkable) | **no** on the restraint run | 1.5 min / 0.6 min | 91k / 87k |
| Haiku 5.5 | 17/17 | 10/10 | 15/15 | yes, both | 3.6 min / 1.6 min | 143k / 107k |

List prices per million tokens (input/output): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50.

## Notes

- **No model can be ranked above another on quality.** All three hit the ceiling on both checklists. These are two small, made-up PRs with one run each, and real PRs are bigger.
- **Undeclared helpers.** Sonnet and Haiku flagged `zipDrafts` / `toJsonFile` / `downloadFile` / `showToast` in `draftStore.ts` as P1, because they're used but not imported. Opus held this back, since other files in the diff also use undeclared names. That's a defensible call either way, and with a local clone any model could check.
- **Severity varies by about one level** between models: `hasUnreadMessages` is P1 for Sonnet and Haiku but P3 for Opus, and the `ReadOnlyPlaylist` LSP finding is P3 for Haiku but P1 for the others. Haiku still raised the importer crash itself at P1.
- **Sonnet's missing findings.json.** On the restraint run, Sonnet wrote only the chat preview. In a real run, Step 6 (posting) and the 2.1.0 HTML page both read findings.json. Version 2.1.0 now says outright that it must be written before the preview.
- **Placement check.** I re-ran every findings.json through 2.1.0's `render_preview.py`. It found no comment on a line outside the diff.

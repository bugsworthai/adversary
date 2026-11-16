# AdversaryPR → GitHub Copilot

The AdversaryPR Claude skill, split into the two things GitHub Copilot actually understands.

**Matches skill version 2.16.0** That covers the careful, thorough review approach, the language rules, the design checks
(SOLID, DRY, YAGNI, anti-patterns), and the comment format: every comment gets to the point (it asks the author a short
question only when it helps), states the failure, and ends with a fix as a code snippet, in plain words
(about a 4th-grade reading level).
On GitHub, a fix that replaces exactly the lines it points at is posted as a suggested change (a Commit suggestion
button). The port covers the review rules for Copilot code review (`instructions/`) and the Azure DevOps flow in the
prompt file (`prompts/adversary.prompt.md`). The skill's release notes (`SKILL.md` in `adversary.skill`) list what
changed between versions. These are skill-only: reviewing several PRs at once (the prompt file reviews one PR per
run), `version=` selection (here, the repo's git history is the version history), the `html` preview page, `model=`
(in Copilot, pick the model in the chat's model picker), posting to GitHub PRs (Copilot code review posts its own
comments), and usage counts.

```
AdversaryPR/
├── universal-prompt.md   → paste into any AI review tool, no setup
├── instructions/     → copy to .github/instructions/ in each repo
│   ├── adversarypr-review-style.instructions.md   (applyTo: **)
│   ├── adversarypr-design-principles.instructions.md (applyTo: all source files — SOLID, DRY, YAGNI)
│   ├── adversarypr-anti-patterns.instructions.md  (applyTo: all source files)
│   ├── adversarypr-ios-swift.instructions.md      (applyTo: **/*.swift)
│   ├── adversarypr-android-kotlin.instructions.md (applyTo: **/*.kt, **/*.kts)
│   ├── adversarypr-jvm-backend.instructions.md    (applyTo: **/*.java, **/*.kt)
│   ├── adversarypr-python.instructions.md         (applyTo: **/*.py)
│   ├── adversarypr-go.instructions.md             (applyTo: **/*.go)
│   ├── adversarypr-typescript.instructions.md     (applyTo: **/*.ts, .tsx, .js, .jsx)
│   └── adversarypr-config.instructions.md         (applyTo: **/*.yaml, .yml, .json, .properties, .xml)
├── prompts/
│   └── adversary.prompt.md                      → copy to .github/prompts/
└── references/                                   → worked examples; not loaded automatically
    ├── design-principles.md                      (SOLID with SRP in depth, DRY, YAGNI)
    └── anti-patterns.md                          (anti-pattern catalog)
```

`references/` holds copies of the two reference files from skill version 2.12.0
(`versions/2.12.0/references/ inside `adversary.skill`), with the file pointers reworded for Copilot. Each
principle and anti-pattern gets a before/after example and a "don't flag" list. All examples are
generic (orders, invoices, exports) rather than taken from any real codebase. Append them to the
universal prompt when a tool accepts a long prompt. When the skill ships a new version, re-copy them.

## Which one do you want?

**`universal-prompt.md` — for any tool, right now.** One self-contained block. Paste it into
Copilot Chat, Cursor, CodeRabbit's instructions field, Gemini Code Assist, Windsurf, a GitLab or
Bitbucket AI review config — anything that takes a text prompt. No files to commit, no globs, no
vendor syntax. Start here if you just want it working today.

**`instructions/` — for Copilot code review on github.com.** Copy the whole folder to
`.github/instructions/` in a repo. Copilot code review reads every `*.instructions.md` whose
`applyTo` glob matches a changed file and applies those rules automatically on every PR. No
invocation, no arguments. This is the closest thing to "AdversaryPR runs itself."

**`prompts/adversary.prompt.md` — for the full ADO flow.** Copy to `.github/prompts/`, then type
`/adversary` in Copilot Chat. It keeps everything the skill did: credentials, ADO REST calls,
thread dedup, the preview-and-confirm gate, POSTing threads. Prompt files only work in VS Code,
Visual Studio, and JetBrains — not on github.com.

You can install both. They don't conflict; the prompt file explicitly defers to the instruction
files for rules when they're present.

## Setup

Copilot needs custom instructions enabled. In VS Code, confirm
`github.copilot.chat.codeGeneration.useInstructionFiles` is `true` (the default). For prompt files,
`chat.promptFiles` must be enabled.

For the prompt file, grant it terminal access when it asks — it needs to shell out for `git diff`
and the ADO API calls.

## Three things that will bite you

**Code review reads instructions from the base branch, not your feature branch.** Add these files
in a PR and Copilot won't use them on that PR. They take effect only after the merge. Land them in a
separate housekeeping PR first.

**Copilot code review only works on GitHub PRs.** If your repos live on `dev.azure.com`, the
`instructions/` folder does nothing there — Copilot code review can't see ADO. Use the prompt file
instead, or mirror the repos to GitHub.

**Kotlin gets both rule sets.** `.kt` matches the Android glob and the JVM backend glob, because
Copilot's `applyTo` can't distinguish an Android module from a Spring service by extension alone.
Both files open with a scope check telling the model which set applies. If your repos are cleanly
split — one is all Android, another all backend — tighten the globs per repo and drop the file that
doesn't apply.

## Trimming per repo

Every file is standalone. In the iOS repo, keep `review-style`, `ios-swift`, and `config`, and
delete the rest — fewer irrelevant rules in context means better-targeted comments.

Keep `adversarypr-review-style.instructions.md` everywhere. It carries the P1–P5 severity model and
the comment format that the language files assume.

Keep `adversarypr-design-principles` and `adversarypr-anti-patterns` everywhere too. They apply to
every language, and each opens with the gates that keep design comments from turning into noise:
the diff has to cause the issue, the reviewer has to name a concrete cost, and repo conventions
win. Each file is kept under 4,000 characters, because Copilot code review has historically read
only the first 4,000 characters of an instruction file. The longer worked examples live in
`references/` for that reason.

Note that a `.instructions.md` file with no `applyTo` is silently ignored by code review. If you add
your own, always set the glob.

## Docs

- [Path-scoped custom instruction files](https://github.blog/changelog/2025-09-03-copilot-code-review-path-scoped-custom-instruction-file-support/)
- [Customizing Copilot code review](https://docs.github.com/en/copilot/tutorials/customize-code-review)
- [Repository custom instructions](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
- [Prompt files](https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/your-first-prompt-file)

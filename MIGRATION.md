# AdversaryPR: moving to a new machine and keeping it going

This folder is the whole AdversaryPR project: the skill's source, the released versions (2.10.0 and later; earlier ones were retired), the Copilot port, and the test workspace. It's everything you need to install it on another machine and keep editing it there. The skill is at version **2.9.0** as of 2026-11-13. `CLAUDE.md` in this folder gives Claude the project rules automatically when you open the folder in Claude Code.

## What's in here

```
adversarypr/
├── MIGRATION.md              ← this file
├── CLAUDE.md                 ← project rules Claude Code loads automatically
├── assets/logo.svg           ← the logo the Step 0 banners in SKILL.md are drawn from
├── adversary.skill         ← the built package; upload this to the org, and it is the frozen-version baseline
├── tools/build_skill.py      ← checks, packages, and installs the skill
├── tools/tests/test_telemetry.py   ← client telemetry tests
├── tools/tests/test_render_preview.py   ← preview renderer tests (ranges, suggestions, code blocks)
├── skill-source/
│   ├── adversary/            ← the skill source (edit here)
│   │   ├── SKILL.md          ← picks the version, plus version table and release notes
│   │   └── versions/
│   │       ├── 2.10.0/                       ← released, frozen
│   │       └── 2.11.0/       ← latest: instructions.md, references/, scripts/render_preview.py
│   ├── adversary/scripts/    ← telemetry.py and telemetry_constants.py (opt-in usage counts)
│   └── adversary-workspace/ ← test inputs, checklists (evals/evals.json), and benchmark summaries
└── AdversaryPR/              ← GitHub Copilot port (instructions, prompt file, universal prompt)
```

## Set up on the new machine

You need Claude Code (the desktop app's Code tab or the `claude` CLI), Python 3.8 or later, `git`, and `curl`. Python is used by the build script and by the `html` preview.

1. **Clone the repo** anywhere, for example `~/Projects/adversary` (`gh repo clone Curtisspope/adversary`).
2. **Install the skill for your user:**
   ```bash
   cd ~/"Projects/adversary" && python3 tools/build_skill.py --install
   ```
   This checks the source, rebuilds `adversary.skill`, and copies the skill to `~/.claude/skills/adversary/`. On Windows that's `%USERPROFILE%\.claude\skills\adversary\`.
3. **Remove old installs, if the machine has them.** `~/.claude/skills/adversarypr/` (the 2.3.0 name), `~/.claude/skills/snipdragon/`, and an old `~/.claude/commands/snipdragon.md` still answer `/adversarypr` or `/snipdragon` with the old name (the command file with the 1.0.0 text). Delete them.
4. **Credentials aren't in the repo, on purpose.** The first time you run `/adversary`, it asks for your Azure DevOps username and a PAT, then asks whether to save them to `~/.ado-pr-review-creds.json`. Make a new PAT for the new machine rather than copying the old file over. Give it the narrowest scopes your org allows that can still read pull requests and post PR comments. Code (Read & write) covers both.
5. **Optional: a local clone of the repos you review.** Run `/adversary` from inside the clone, and AdversaryPR diffs locally and reads callers. Without a clone, it uses the Azure DevOps API.
6. **Check it works:** `/adversary version=list` should print the versions table, with 2.10.0 marked latest. Then do a real dry run with the HTML page: `/adversary <PR number> ; dry run ; html`.

**Org copy.** The org's `anthropic-skills:adversary` is separate from your local install. To update it, upload `adversary.skill` wherever your org manages Claude skills. Until someone does, the org copy stays at the version last uploaded.

## Using it

```
/adversary 38842                              latest version, PR in the default iOS repo
/adversary https://dev.azure.com/…/pullrequest/1234
/adversary 38842 38901 39010 ; dry run        several PRs at once, nothing posted
/adversary 38842 ; html                       web-page preview with diff context and a picker
/adversary 38842 ; model=haiku                review runs on Haiku (also sonnet, opus, fable)
/adversary 38842 ; version=2.10.0             a specific older version
/adversary version=list                       versions and release notes
```

Options go after the first `;` and combine freely: `/adversary 38842 38901 ; dry run ; html ; model=sonnet`. Nothing is ever posted until you pick comments at the prompt.

**GitHub pull requests .** Targets: `https://github.com/{owner}/{repo}/pull/{n}` or `{owner}/{repo}#{n}`. A plain number is still an Azure DevOps PR, and the two can be mixed in one run (`/adversary 38842 acme/orders-api#101 ; dry run`). Each PR's `pr.json` records `"provider": "ado"` or `"github"`, and a GitHub PR's run folder and selection key is `gh-{repo}-{n}` (for example `gh-orders-api-101`), so numbers never collide with Azure DevOps IDs.
- **Credentials:** the `gh` CLI if `gh auth status` succeeds (no token handled). Otherwise `GITHUB_TOKEN` or `GH_TOKEN` from the environment, used with curl. If neither exists the skill says to run `gh auth login`, or to set `GITHUB_TOKEN` to a fine-grained token with Pull requests read and write and Contents read, and skips the GitHub PRs. GitHub tokens are never saved or printed, and review agents never get credentials. A GitHub-only run never asks for Azure DevOps credentials.
- **Fetch (main session):** `GET /repos/{o}/{r}/pulls/{n}` (closed or merged PRs are skipped), the diff via `Accept: application/vnd.github.v3.diff` (or local git), and `GET .../pulls/{n}/comments` for duplicate detection.
- **Post (only after approval, never on dry run):** one review per PR, `POST /repos/{o}/{r}/pulls/{n}/reviews` with `commit_id` (head SHA), `event: COMMENT`, and `comments` of `{path, line, side: RIGHT, body}`. If GitHub rejects the batch (for example 422, line not in the diff), the remaining comments are posted one at a time with `POST .../pulls/{n}/comments`, once each, and failures are reported. Comments appear as the signed-in user. GitHub paths have no leading slash.
- **Not verified against the real API.** The GitHub flow was written from the API docs and exercised only offline. Try it on a throwaway PR with `; dry run` first, then without.

**Choosing a model.** On the 2026-11-11 tests, Opus 5.5, Sonnet 5.5, and Haiku 5.5 all scored 17/17 and 10/10, with every comment on a valid line. Sonnet and Haiku were 3 to 7 times faster than Opus, and much cheaper per token. Those were two small, made-up PRs with one run each, so compare on a real PR before settling (`; dry run ; html ; model=haiku`). Details: `skill-source/adversary-workspace/iteration-3-models/benchmark.md`.

**Optional Claude Code settings** (in `~/.claude/settings.json` under `"env"`):
- `CLAUDE_CODE_SUBAGENT_MODEL`: the default model for multi-PR review agents when you don't pass `model=`.
- `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`: forces that model even over `model=`. Leave it unset if you want `model=` to work.
- `CLAUDE_CODE_EFFORT_LEVEL`: lowers token use. Effort levels weren't tested with this skill.

## Editing from here on

**The one rule: never change a released version.** Every folder under `versions/` is frozen once it's in a built package, so `version=2.10.0` behaves the same forever. `tools/build_skill.py` enforces this. It refuses to build if any version folder differs from the last `adversary.skill`.

To make a change, cut a new version:

1. **Copy the latest folder:** `cp -R skill-source/adversary/versions/2.10.0 skill-source/adversary/versions/<new>`.
   - Use a patch bump (2.2.1) for fixes, a minor bump (2.3.0) for new options or rules, and a major bump (3.0.0) for behavior changes people would notice.
2. **Edit only the new folder.** Update the version strings inside it: the review-agent prompt line, the Step 5 version line, the "Which model ran" example, and `--version` on the `render_preview.py` command. `grep -n "2\.8\.0" versions/2.10.0/instructions.md` finds them all.
3. **Update `skill-source/adversary/SKILL.md`:**
   - the **Latest version** line
   - the **Available versions** table: move "(latest)" and the bold to the new row
   - a **Release notes** entry (Added / Changed / Fixed / Unchanged)
   - the `description` in the frontmatter, if the new version can do something new
   - Step 0 item 3, if the new version adds an option that older versions should refuse
4. **Build:** `python3 tools/build_skill.py --install`. This checks everything, writes `adversary.skill`, and installs it locally.
5. **Test** (below), then upload `adversary.skill` to the org.
6. **Update the Copilot port** if the rules changed (below).
7. **Add the version to the collector:** add it to `KNOWN_VERSIONS` in the private web repo's `functions/constants.py` (latest: 2.10.0) and redeploy the collector (that repo's test fails if you forget).

**Rules the build checks for you:**
- The frontmatter may only use `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. Org uploads reject other keys, such as `model:`.
- The description is 1024 characters or fewer, with no `<` or `>`.
- No `SKILL.md` anywhere except the top of the skill.
- The versions table, the "Latest version" line, the release notes, and the folders all agree.

**Content rules** (from the original request; the build doesn't check these):
- Keep every example generic (orders, invoices, exports). Never use real employer or customer file names, people, or code.
- The PAT must never be printed, logged, or written into the project. Review agents never get it.
- Nothing posts without the user's approval.

## Anonymous usage counts

Opt-in, off until the user says yes. The dispatcher (`SKILL.md` Step 0 item 6) runs `skill-source/adversary/scripts/telemetry.py`, which asks once on first run and keeps the answer in `~/.adversary/telemetry.json` (`{"consent": "on"|"off"}`, folder 0700, file 0600).

- **Sent when on:** schema version, event `run`, skill version, and `dry_run`, `html`, `model` (`default`/`haiku`/`sonnet`/`opus`/`fable`), `version_pinned`. Nothing else: no code, PR content or numbers, repo/org/project names, usernames, token, paths, machine or install ID. `telemetry.py preview --version X ...` prints the exact JSON.
- **Turn off:** `python3 ~/.claude/skills/adversary/scripts/telemetry.py set off`, or `ADVERSARY_TELEMETRY=0` / `DO_NOT_TRACK=1` (these also stop the question).
- **Never blocks a review:** 2 second timeout, every error swallowed, no output.
- **Collector:** the private web repo's `functions/` (Firebase Functions 2nd gen, Python) stores per-day counters only, and does not write IP addresses to its database; hosting request logs may still hold them briefly. Deploy steps and the abuse caveat (no rate limiting or App Check yet) are in that repo's `functions/README.md`. The endpoint `https://adversarypr.com/api/collect` is not live until the client deploys it; until then sends fail silently.
- **Offline tests never send:** set `ADVERSARY_TELEMETRY=0` and skip the telemetry step (the test prompt below says so).
- **Tests:** `python3 -m unittest tools/tests/test_telemetry.py` here, and `cd functions && python3 -m unittest discover -s tests` in the web repo.

## Comment format 

Every comment gets to the point and ends with a fix as code. In order: a bold title; the problem and, only when the author is the one who knows the answer, one genuine, specific question (never rhetorical, never asked when reading the callers answers it; with no required opener ("I noticed that ..." is fine on some comments, not all)); why it matters (the concrete failure, never softened by the question); the sentence "Please take a look at the suggested fix below, unless this was intentional."; the fix or way forward as a fenced code block of at most about 15 lines (one recommended fix, at most one alternative in a line after it; a skeleton or steps when no code-level fix exists); then the footer, which the main session appends. Everything is gentle (suggestions like "you could" or "one way is", never orders) and written at about a 4th-grade reading level (short sentences, everyday words; code and names stay as they are).

**findings.json fields (both optional):**
- `startLine`: first line of a multi-line anchor, with `line` as the last. Absent or equal to `line` means a single line. Every line in the range must be an added or context line of the same hunk.
- `suggestion`: `true` when `content` has a ```` ```suggestion ```` block.

**GitHub suggestion rule.** Only on GitHub, and only when the snippet replaces exactly the anchored line or range, the fix is a ```` ```suggestion ```` block (GitHub shows a "Commit suggestion" button that applies it as a new commit). Otherwise use a normal language block. On Azure DevOps never use `suggestion`: use a language block or a ```` ```diff ```` block. Posting: Azure DevOps `rightFileStart.line` = `startLine` (or `line`), `rightFileEnd.line` = `line`. GitHub `line` = last line, plus `start_line` and `start_side: "RIGHT"` when `startLine` < `line`. The Commit button is GitHub's own feature and has not been exercised against a real PR.

**Offline checks:** the renderer warnings above, and the extra assertions in `evals.json` for evals 1, 2, 7 and 8 (question, the fixed sentence, a fenced fix, no `suggestion` on Azure DevOps, exact-replacement for `suggestion` on GitHub).

## Testing

Tests run **offline**: a background agent follows the skill on a saved diff, with no Azure DevOps calls. They live in `skill-source/adversary-workspace/`:
- `inputs/`:
  - `eval1-mixed-stack.diff`: planted bugs, design problems, and traps
  - `eval2-conventions-heavy.diff` plus `eval2-CLAUDE.md`: patterns the repo's own conventions allow, which a good review leaves alone
- `evals/evals.json`: the checklist each run is graded against
- `iteration-N/`: past runs, each with the output and a grading note

To test a new version, ask Claude in this folder something like *"Run eval 1 and eval 2 against the latest AdversaryPR version, offline, and grade them against evals/evals.json"*. That's enough with `CLAUDE.md` in place. The agent prompt that past runs used:

```
Skill path: <this folder>/skill-source/adversary. Read SKILL.md there and follow it.
Invocation to simulate: `/adversary 101 ; dry run`   (add ; html, ; model=haiku, etc. to test options)

This is an OFFLINE TEST. No Azure DevOps, no network. Adapt only these parts:
- Telemetry: skip Step 0 item 6 entirely. Set ADVERSARY_TELEMETRY=0 and do not run telemetry.py at all.
- Steps 1 and 2: skip. Use RUN_DIR = <iteration folder>/eval-1-mixed-stack/run-1/outputs/run
- Step 3: create RUN_DIR/PR-101/ with diff.patch = a copy of inputs/eval1-mixed-stack.diff,
  threads.json = [], an empty conventions/ folder, and pr.json with org Contoso,
  project Shop, repo ios-app, apiBase "offline", prId 101, title "…", url "offline",
  branches/SHAs "unknown", localClone null, conventions [], error null.
  (Eval 2: PR 102, inputs/eval2-conventions-heavy.diff, and conventions/CLAUDE.md = inputs/eval2-CLAUDE.md.)
- Everything else exactly as the instructions say. At Step 5, print the preview, then stop after
  the selection question. Don't wait and don't post.
Save the full output to <…>/outputs/review.md. Modify nothing outside that outputs folder.
```

**Offline GitHub eval (7).** Same prompt as above with these changes. Eval 7: invocation `/adversary https://github.com/acme/orders-api/pull/101 ; dry run`. Skip Steps 1 and 2 (fake the GitHub login as `test-user`, so the footer name is `test-user`), and in Step 3 use `RUN_DIR/PR-gh-orders-api-101/` with the same diff and an empty `threads.json` and `conventions/`. `pr.json` is `{"provider": "github", "owner": "acme", "repo": "orders-api", "apiBase": "offline", "prId": 101, "title": "...", "url": "offline", "sourceBranch": "unknown", "targetBranch": "unknown", "sourceSha": "unknown", "targetSha": "unknown", "localClone": null, "conventions": [], "commentAs": "test-user", "error": null}`. No call to GitHub or Azure DevOps.

**Quick placement check**, with no model involved: run the renderer on any finished run folder. It prints a `WARNING` for any comment whose line isn't in the diff, any file path with the wrong slash form for its provider (Azure DevOps needs a leading `/`, GitHub must not have one), and any `#n` that the platform would turn into a link. From 2.7.0 it also warns when a `startLine`..`line` range is not all added or context lines of one hunk, when a ```` ```suggestion ```` block appears on an Azure DevOps PR or in a finding with no valid anchor, and when a finding's `suggestion` flag and its content disagree. Its tests: `python3 -m unittest tools/tests/test_render_preview.py`.

```bash
python3 skill-source/adversary/versions/2.10.0/scripts/render_preview.py <run folder> --version 2.10.0
```

## The Copilot port (`AdversaryPR/`)

This is the same rules, split into what GitHub Copilot understands. `AdversaryPR/README.md` explains each piece. When you change the rules in a new version:
- Make the same change in the matching `AdversaryPR/instructions/*.instructions.md`. Keep each file under 4,000 characters (`wc -c`), because Copilot code review has historically read only the first 4,000.
- Re-copy `versions/<new>/references/*.md` into `AdversaryPR/references/`. Point the "see references" lines at the `adversarypr-*.instructions.md` files instead.
- Update the "Matches skill version" line in `AdversaryPR/README.md`.

Multi-PR reviews, `version=`, `html`, and `model=` are skill-only.

## Open items

- **Org copy:** someone needs to upload the latest `adversary.skill` to replace the old org version.
- **Project-specific rules:** the iOS P3 rules still name Project-specific types (`AppLog`, `FeatureFlags`, `Color+Tokens.swift`). They apply only when a repo's own CLAUDE.md or AGENTS.md mentions them, but a future version could make them generic.
- **Copilot prompt file:** it reviews one PR per run. Multi-PR support could be added.
- **Model test depth:** the model comparison was one run per model on small PRs. It's worth repeating on a few real PRs.

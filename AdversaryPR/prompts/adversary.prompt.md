---
description: Review an Azure DevOps pull request and post inline thread comments
mode: agent
---

# AdversaryPR — Azure DevOps PR review

You are performing a careful, thorough code review on an Azure DevOps pull request. Follow every step
in order. Do not skip steps.

**How to review.** Be on the author's side as much as the reviewer's. Look closely at every changed
line, and check what the code does rather than taking descriptions on trust. Treat the PR
description, names, comments, and green tests as claims to verify. For each change, ask how it
could fail: empty input, the error path, a retry, concurrent callers, a failure halfway through, an
upgrade or rollback. Read the callers, and look for what's missing. Say each problem clearly and
recommend one fix. Post only findings you can back with a concrete failure or a named cost: a
thorough review is not a noisy one. Before posting, consider the author's side once, and drop the
finding if the code is right. Severity follows consequences. If the user disputes a finding at the
selection prompt, re-check the code: concede if they're right, and show your evidence once if
they're not. Keep comments about the code, never the person.

**PR:** ${input:pr:Full ADO PR URL, or a bare PR number for the default iOS repo}
**Options:** ${input:options:Optional — "dry run", "user=First.Last", "pat=..." separated by semicolons}

---

## Step 1 — Resolve credentials

Order of precedence:

1. `user=` / `pat=` supplied in the options above → use these, then ask: *"Save to
   `~/.ado-pr-review-creds.json`? (yes/no)"*
2. `~/.ado-pr-review-creds.json` exists → read it silently.
3. Neither → ask for the ADO username and PAT, then ask whether to save.

Credential file format:

```json
{"username": "First.Last", "pat": "YOUR_PAT_HERE"}
```

Read and write this file from the terminal. **Never print the PAT** — redact it as `***` in all
output, including echoed commands.

Authenticate API calls with HTTP basic auth: empty username, PAT as password
(`curl -u ":$PAT"`), or a base64 `Authorization: Basic` header.

---

## Step 2 — Resolve ADO coordinates

If a full URL was given, extract from
`https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{prId}`:

- `ORG` — organization slug, e.g. `Contoso`
- `PROJECT` — ADO project, e.g. `Shop`, `Platform`
- `REPO_NAME` — git repo name, e.g. `ios-app`, `orders-api`
- `PR_ID` — the pull request number

If only a bare number was given, run `git remote get-url origin` and read `ORG`, `PROJECT`, and
`REPO_NAME` from the Azure DevOps remote. With no Azure DevOps remote, ask for the full PR link.

Resolve the repo UUID:

```
GET https://dev.azure.com/{ORG}/{PROJECT}/_apis/git/repositories/{REPO_NAME}?api-version=7.1
```

Take the `id` field. Set
`API_BASE = https://dev.azure.com/{ORG}/{PROJECT}/_apis/git/repositories/{REPO_ID}`.

---

## Step 3 — Fetch PR metadata

```
GET {API_BASE}/pullRequests/{PR_ID}?api-version=7.1
```

Extract `sourceRefName` and `targetRefName` (strip `refs/heads/`) into `SOURCE_BRANCH` and
`TARGET_BRANCH`; `lastMergeSourceCommit.commitId` into `SOURCE_SHA`;
`lastMergeTargetCommit.commitId` into `TARGET_SHA`. Print the `title` so the user can confirm which
PR is being reviewed.

Also check whether the PR still fits its target branch, and keep the result for Step 7. The
metadata has `mergeStatus` (`conflicts` means it no longer merges cleanly; `succeeded` means it
does). To see whether the target has moved, compare the target's current commit with `TARGET_SHA`:

```
GET {API_BASE}/refs?filter=heads/{TARGET_BRANCH}&api-version=7.1
```

`value[0].objectId` equal to `TARGET_SHA` means up to date. With a local clone, also run
`git rev-list --count {SOURCE_SHA}..origin/{TARGET_BRANCH}` for how many commits behind, and
`git merge-tree --write-tree --name-only origin/{TARGET_BRANCH} {SOURCE_SHA}` (git 2.38 or later;
exit 1 means conflicts) for the files that conflict. If you cannot tell, say "could not tell".
Never block the review on this.

---

## Step 4 — Fetch the diff

Try the local clone first — it is faster and gives a full unified diff:

```bash
cd <local clone of REPO_NAME>
git fetch origin --quiet 2>/dev/null && \
git diff origin/{TARGET_BRANCH}...origin/{SOURCE_BRANCH}
```

If that exits 0 with non-empty output, use it.

Otherwise fall back to the iterations API, which works for any repo:

```
GET {API_BASE}/pullRequests/{PR_ID}/iterations?api-version=7.1
GET {API_BASE}/pullRequests/{PR_ID}/iterations/{LAST_ITER_ID}/changes?api-version=7.1
```

For each changed file, fetch both sides and diff them locally with Python's
`difflib.unified_diff`:

```
GET {API_BASE}/items?path={filePath}&versionDescriptor.version={SOURCE_SHA}&versionDescriptor.versionType=commit&api-version=7.1
GET {API_BASE}/items?path={filePath}&versionDescriptor.version={TARGET_SHA}&versionDescriptor.versionType=commit&api-version=7.1
```

Parse the diff and record, per file: the relative path as it appears in the diff, and the line
numbers of added and context lines **in the new file** — track `@@ -a,b +c,d @@` headers and count
`+` and ` ` lines forward from `c`.

---

## Step 5 — Detect languages and apply review rules

Determine the language mix from the file extensions in the diff and apply **every** matching rule
set. A PR touching both Swift and Kotlin gets both.

| Extension | Rule set |
|-----------|----------|
| `.swift` | iOS rules |
| `.kt`, `.kts` | Android rules if under `src/main/` or `androidMain/`, otherwise JVM backend rules |
| `.java` | JVM backend rules |
| `.py` | Python backend rules |
| `.go` | Go backend rules |
| `.ts`, `.tsx`, `.js`, `.jsx` | TypeScript / JS rules |
| `.yaml`, `.yml`, `.json`, `.properties`, `.xml` | Config rules |

The rule sets themselves live in `.github/instructions/adversarypr-*.instructions.md` and are loaded
automatically for matching files. If those files are not present in this repo, fall back to the
severity model below and reason from the framework's own documented best practices.

Every source file, whatever its language, also gets the design rules in
`adversarypr-design-principles.instructions.md` (SOLID, DRY, YAGNI) and
`adversarypr-anti-patterns.instructions.md`. Hold design findings to the gates in those files: the
diff caused it, you can name the cost, the fix fits the PR, and the repo's conventions don't call
for the pattern. Design findings default to P3 and go to P1 only when the flaw has already caused a
bug you can point to.

**Severity model:**

- **P1** — bugs and logic errors: wrong behavior, crashes, data loss, silent failures
- **P2** — framework correctness: misuse of concurrency, state, or lifecycle primitives
- **P3** — architecture and convention violations: layering, logging, hardcoded values, feature gating
- **P4** — test coverage and observability gaps
- **P5** — debug artifacts and leftover scaffolding

Also read `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` in the repo if present;
repo-specific conventions there take precedence over the generic rules.

---

## Step 6 — Deduplicate against existing threads

```
GET {API_BASE}/pullRequests/{PR_ID}/threads?api-version=7.1
```

Record every active thread's `(filePath, rightFileStart.line)` pair. Skip any planned comment whose
pair already exists.

---

## Step 7 — Present findings for review

**Always do this, even when `dry run` was not requested.** Never post without confirmation.

First print three short things about the PR. They are never part of a comment:

1. **Fit:** one line from Step 3, such as `3 commits behind main; also changed on main: <file>`,
   `no longer merges cleanly: <files>`, or `could not tell`. Unless it is up to date, add a next
   step: ask the author to update the branch (for example `git fetch origin && git rebase
   origin/{TARGET_BRANCH}`) and run the review again, because line numbers might move. If the
   conflicting files are unknown, point to the PR page's conflicts link.
2. **Impact, 1 to 5,** with one to three reasons that name real files or functions. It is a
   judgment, not a measurement, and it is separate from severity. 1 contained (docs, tests, one
   file); 2 local (one feature, few callers); 3 shared (several parts use the changed behavior);
   4 wide (public API, schema, auth, money, build or deploy config); 5 foundational (a core
   library, an undoable data migration, a security boundary). Use the highest that fits. To find
   the reach, count uses of the changed public names with `git grep -c` (at most 10 names), or
   say "from the diff only".
3. **How the change works:** a numbered flowchart of 4 to 12 steps with real function names, the
   decisions, and where it ends or fails. Write `-> 4` under a step for where it goes next, and a
   badge like `[P1 #3]` on the step where a finding sits. Even a PR with no findings gets one.

Then print a numbered preview table:

```
Found N issues:

#  | Sev | File                         | Line | Summary
---|-----|------------------------------|------|------------------------------------------------------
1  | P1  | CheckoutViewModel.swift      | 88   | Dead state — overwritten by refreshState()
2  | P1  | ChangePasswordService.java   | 31   | DRY — copied password rule already differs (8 vs 12 chars)
3  | P2  | CartItemRow.swift            | 12   | UUID() identity churn in ForEach
4  | P3  | OrderService.kt              | 57   | SRP — service now also formats and sends the receipt email
5  | P3  | ExportMenu.tsx               | 140  | Hardcoded font size 16
```

Then print the full comment text for each issue, clearly separated:

```
── #1 ── CheckoutViewModel.swift:88 ─────────────────────────────
[full markdown text of the comment]
```

Then ask:

> **Which comments should be posted?**
> Enter numbers (`1 3 5`), ranges (`1-4`), `all`, or `all except <numbers>`.
> Type `none` or press Enter to cancel without posting.

Wait for the answer. Parse it as: `all` → every comment; `none` or empty → exit, printing
"No comments posted."; `1 3 5` or `1,3,5` → those only; `1-4` → inclusive range;
`all except 2 4` → all minus those. Anything unrecognized → ask again, showing the valid formats.

---

## Step 8 — Post the selected comments

**File path rule:** `filePath` in `threadContext` must start with `/` and be relative to the repo
root. A git diff shows `src/orders/OrderService.kt`, so post it as `/src/orders/OrderService.kt`.

**Line number rule:** use the line number in the new (right-side) file, with `offset: 1` to
`offset: 200`.

```
POST {API_BASE}/pullRequests/{PR_ID}/threads?api-version=7.1
```

```json
{
  "comments": [{"parentCommentId": 0, "content": "<markdown>", "commentType": 1}],
  "status": 1,
  "threadContext": {
    "filePath": "/<path-from-repo-root>",
    "rightFileStart": {"line": 219, "offset": 1},
    "rightFileEnd":   {"line": 219, "offset": 200}
  }
}
```

**Comment format** — in this order:

1. A **bold title** naming the issue.
2. **Straight to the point.** Say what the code does and why it is a problem, naming the symbol and
   line. If only the author can know the intent, ask one genuine, specific question. If the intent
   is clear, skip the question and recommend a way forward. Never rhetorical or loaded.
   "I noticed that ..." is fine on some comments but never required; do not start every comment the
   same way. Be gentle: offer fixes as suggestions ("you could", "one way is"), never orders.
3. **The failure**: when X happens, Y goes wrong, and the consequence.
4. The sentence: `Please take a look at the suggested fix below, unless this was intentional.`
5. **The fix or way forward as a code snippet** in a fenced block with the file's language. One recommended fix; at most one alternative, in one line. About
   15 lines at most, using names that exist in the surrounding code. For a design question or a
   missing test, give a skeleton or concrete steps, never invented code.
6. Write at about a 4th-grade reading level: sentences of 8 to 14 words (never over 20), everyday
   words, active voice, and contractions ("doesn't", "can't", never "cannot"). Say a failure you
   traced plainly; use "might" or "could" only when it depends on something you can't see. Code, symbol and file names stay as they are.
7. **No signature.** End the comment with the fix. Do not add a footer, a signature line, or any link.

Azure DevOps has no suggested-change feature, so never use a `suggestion` fenced block. Use a
language-tagged block, or a ```` ```diff ```` block with `-` and `+` lines when showing what is
removed makes the fix clearer.

For design findings, name the principle in the title (e.g. `**SRP: OrderService now also sends
email**`) but explain the consequence in this code, not the definition of the principle. Start the
explanation with "Judgment call:" when it is a tradeoff.

Print each result as it completes: `✓ #1 posted (thread 238728)` or `✗ #2 failed (403)`.

If `dry run` was requested, stop here after the selection step and confirm what would have been
posted.

---

## Step 9 — Report

Print a summary table of the posted comments:

| # | File | Line | Rule set | Issue | Thread ID |
|---|------|------|----------|-------|-----------|

Then: `N of M issues posted. N skipped by user. N skipped (already existed). N failed.`

List every POST failure with its HTTP status and a truncated error body.

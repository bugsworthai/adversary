---
name: adversary
description: Helps you keep up with AI-written pull requests: a faster, more confident review for Azure DevOps and GitHub. Reviews one or more PR's, asks the author questions when it helps, explains in plain words, shows each fix as a code snippet (on GitHub, as a suggested change when it replaces exactly the lines it points at), and posts inline comments only after you approve them. Supports iOS (Swift), Android (Kotlin), and backend (Java/Kotlin/Python/Go/TypeScript), with design checks for SOLID (SRP in depth), DRY, YAGNI, and anti-patterns. Add html for a branded web-page preview with charts, a how-it-works flowchart, and a PDF download that shows each comment with the code it points at, and model=haiku, sonnet, opus, or fable to pick the reviewing model per run. Runs the latest version unless you pass version=X. Use for /adversary, dev.azure.com pull request links, github.com pull request links, or any request to review or comment on ADO or GitHub PR's.
---

# AdversaryPR

This file chooses which version of AdversaryPR runs, then hands off to it. The review instructions live in `versions/<version>/instructions.md`. Released versions are frozen and never change after release, so `version=1.1.0` behaves the same next year as it does today.

**Latest version: 2.22.0**

## Step 0 — Pick the version

Arguments are in `$ARGUMENTS`.

1. Look anywhere in the arguments for `version=<value>`. The value runs to the next `;` or whitespace. It's case-insensitive, and a leading `v` on the value is fine (`version=v2.10.0`). If `version=` appears more than once with different values, ask which one the user meant.
   - **No `version=`**, or `version=latest` → use the latest version above.
   - **`version=list`** → print the "Available versions" table and the release notes below, then stop. Don't review anything.
   - **An exact version** (`2.10.0`) → use it.
   - **A partial version** (`2` or `2.10`) → match it against whole version components, not as text: `2` means any `2.x.x`, and `2.10` means any `2.10.x`. Use the highest match, comparing component by component as numbers (so `2.10.0` beats `2.9.0`). `2` → `2.22.0` today.
   - **No match, or anything else** → say the version doesn't exist, print the "Available versions" table, and stop. Never fall back to a different version silently, because the user asked for a specific one.

   A "released version" is a row in the Available versions table whose folder exists under `versions/`.
2. Remove the `version=` option, then tidy what's left: drop empty options between `;`s, and drop a trailing `;`. For example, `38842 ; version=2.10 ; dry run` becomes `38842 ; dry run`. Leave everything else exactly as typed.
   Also handle `-nobranding` or `nobranding` as an option here: it means the same as `branding=off`, and is removed from the arguments like `branding=`. Also handle `branding=on` or `branding=off` here (case-insensitive, value runs to the next `;` or whitespace; any other value: say the allowed values and stop). Resolve **BRANDING** as: the option if given, else the environment variable `ADVERSARY_BRANDING` (read it with `printenv ADVERSARY_BRANDING`; `on`, case-insensitive, means on, anything else or unset means off), else `off`. The option wins over the variable. Remove `branding=` from the arguments like `version=`. Only versions 2.6.0 and later use it (before 2.16.0 the default was on; from 2.16.0 it is off, so no footer or link is added unless it is turned on); tell the chosen version's instructions "BRANDING is on" or "BRANDING is off" at step 4. Never print, explain, or list these options in any output.
3. Every version still available supports every option, so there is nothing to refuse.
4. **Print the banner now.** Your very first output of the run is the banner from the "Banners" section below. Print it before you read any file, run any command (telemetry included), or write any other text, and before you start the review. You do not need a tool to know the version: items 1 to 3 only read the arguments. Use the **latest-version banner** when the version chosen in item 1 is the latest, and the **older-version banner** for any other version. Fill in `<version>`. Print it in a code block, copied exactly, with every leading space kept. If the version's instructions add to the version line (2.2.0 and later add the review model), include their addition on the same row as the version. The model is known from `model=` before the review starts, or it is "this session's model". Print the banner once per run, including for `version=list` and for any refusal or stop. It appears on every run, with no exception, whatever other options were given.
5. Read `versions/<version>/instructions.md` (relative to this skill's folder) and follow it exactly, as though it were this skill's own instructions:
   - Wherever it says `$ARGUMENTS`, use the arguments left after step 2.
   - Resolve every relative path it mentions (such as `references/anti-patterns.md`) against `versions/<version>/`, not the skill root. Review agents get the full `versions/<version>/` path.
6. **Anonymous usage counts** (do this after the banner is printed; skip this item on `version=list`, on the refusals in item 3, and in offline tests, where `ADVERSARY_TELEMETRY=0` is set or the test prompt says to skip it). Run these with `python3` from this skill's `scripts/` folder, never print their output, ignore any failure, and never let them delay or change the review. Credentials are never involved.
   - Run `python3 scripts/telemetry.py status`. It prints `ask`, `on`, or `off`.
   - **`ask`**, and this session can ask the user a question: ask exactly this, once, and record the answer. If the session can't ask, do nothing.
     > Anonymous usage counts are off until you say yes. The skill asks once. If you agree, it sends the skill version and which options you used (dry run, html, model, pinned version) and nothing else: no code, no PR content, no repo or org names, no token. Turn it off any time.
     - Yes: `python3 scripts/telemetry.py set on`. No: `python3 scripts/telemetry.py set off`. Tell the user in one line that `python3 scripts/telemetry.py set off` (or `ADVERSARY_TELEMETRY=0`) turns it off any time.
   - **`on`**: run `python3 scripts/telemetry.py send --version <version>` and add `--dry-run` if the options had `dry run`, `--html` if they had `html`, `--model <name>` if they had `model=<name>`, and `--pinned` if the user typed `version=` with an exact or partial version (not `latest`). Run it in the background or with a short timeout, and discard its output.
   - **`off`**: do nothing.

## Banners

Latest version:

```
             /---------\
           /-           -\
         /-               -\
        /                   \
       /                     \
      /     _____________     \
     /     |             |     \
    /       ----\   /----       \      AdversaryPR v<version> (latest)
   /            |   |            \
 /-             |   |             -\
/               |   |               \
\_   _____       \ /       _____   _/
  \_/     \_      -      _/     \_/
            \__       __/
               \_____/
```

Older version:

```
             ###########
           ##@@@@@@@@@@@##
         ##@@@@@@@@@@@@@@@##
        #@@@@@@@@@@@@@@@@@@@#
       #@@@@@@@@@@@@@@@@@@@@@#
      #@@@@@+++++++++++++@@@@@#
     #@@@@@+             +@@@@@#
    #@@@@@@@+++++   +++++@@@@@@@#      AdversaryPR v<version>
   #@@@@@@@@@@@@+   +@@@@@@@@@@@@#
 ##@@@@@@@@@@@@@+   +@@@@@@@@@@@@@##
#@@@@@@@@@@@@@@@+   +@@@@@@@@@@@@@@@#
##@@@#####@@@@@@@+ +@@@@@@@#####@@@##
  ###     ##@@@@@@+@@@@@@##     ###
            ###@@@@@@@###
               #######
```

## Available versions

| Version | Released | Highlights |
|---|---|---|
| **2.22.0** (latest) | 2026-11-20 | Comments use contractions and match their wording to how sure the review is; impact and fit show as a scorecard on the page |
| 2.21.0 | 2026-11-20 | The fit check no longer says "no overlap" when GitHub caps the file list |
| 2.20.0 | 2026-11-20 | Checks the PR still fits its target branch, an impact score, and the how-it-works flowchart on every run |
| 2.19.0 | 2026-11-17 | The HTML page downloads a real PDF (no print dialog) |
| 2.18.0 | 2026-11-17 | Every HTML page explains how the code works in a flowchart with findings pinned to steps; export to PDF or PNG |
| 2.17.0 | 2026-11-17 | Visual HTML preview: charts, flowcharts, AdversaryPR branding on the page |
| 2.16.0 | 2026-11-16 | Comments carry no footer or link by default |
| 2.15.0 | 2026-11-16 | A separate token for each Azure DevOps organization, project or repo; GitHub accounts can be matched to owners |
| 2.14.0 | 2026-11-16 | The logo shows on every run; the HTML preview opens with a clickable link |
| 2.13.0 | 2026-11-14 | The fix sentence is back; comments stay short, plain and gentle |
| 2.12.0 | 2026-11-14 | Comments get to the point, in plain words (about a 4th-grade reading level) |
| 2.11.0 | 2026-11-14 | Tidier comment signatures; the checks are unchanged |
| 2.10.0 | 2026-11-14 | A bare PR number now uses the repo in your current folder |

```
/adversary 38842                        → latest (2.22.0)
/adversary 38842 ; html                 → latest, plus a web-page preview
/adversary 38842 ; model=haiku          → latest, reviewed by Haiku
/adversary 38842 38901 39010 ; dry run  → latest, three PRs reviewed at the same time
/adversary https://github.com/acme/orders-api/pull/101 ; dry run  → latest, a GitHub PR
/adversary 38842 ; version=2.10.0       → exactly 2.10.0
/adversary 38842 ; version=2            → newest 2.x (2.22.0)
/adversary version=list                 → versions and release notes; no review
```

## Release notes
### 2.22.0 — 2026-11-20

**Changed**
- **Friendlier, more honest wording in comments.** Comments use contractions ("doesn't", "can't") instead of "does not" and "cannot". The words also match how sure the review is: a failure the reviewer traced is stated plainly, and "might" or "could" is used only when the outcome depends on something the reviewer can't see. "May not" is avoided because it can mean two things.
- **Impact and fit are a scorecard on the HTML page.** The page shows the impact score as a five-segment meter with its reasons, and the fit result beside it, under each PR's heading. The multi-PR table on the page has Impact and Fit columns.

**Unchanged:** the checks, the evidence standard, severity, the flowchart, and the rule that nothing posts without your approval.

### 2.21.0 — 2026-11-20

**Fixed**
- **The fit check is honest when it cannot see everything.** Found on a real PR: GitHub lists at most 300 files changed on the target branch, so a PR far behind its target could be reported as having no overlap when that was not known. Now, without a local clone, the skill reads the files changed on the target from GitHub's compare answer and finds overlap when it is there. If the list is capped and shows no overlap, the line says the overlap was not fully checked instead of claiming there is none.

**Unchanged:** the rules, the reviewers, the impact score, the flowchart, the comment format, and the rule that nothing posts without your approval.

### 2.20.0 — 2026-11-20

**Added**
- **Does the PR still fit its target branch?** Before any lines are reviewed, each PR is checked for whether it is up to date, behind, changed in the same files as the target, or no longer merges cleanly. It uses read-only git when there is a local clone, and the platform's own merge answer when there is not. The result is printed per PR and never goes into a comment, and the review still runs either way.
- **An impact score for each PR.** A 1 to 5 judgment of how much of the codebase the change can touch (Contained, Local, Shared, Wide, Foundational), with the reasons, such as how many places call the changed code. It is a judgment from a rubric, not a measurement, and it is separate from finding severity.
- **The how-it-works flowchart on every run.** It used to need `html`. Now the chat shows it as numbered steps, with a badge on the step where each finding sits, and `html` still draws it as a picture. Even a PR with no findings gets one.

**Changed**
- The multi-PR summary table has Impact and Fit columns.

**Unchanged:** the rules, the reviewers, the comment format, branding on the page only, no footer or link on comments by default, and the rule that nothing posts without your approval.

### 2.19.0 — 2026-11-17

**Changed**
- **A real PDF download.** With `html`, the skill now saves `preview.pdf` next to the page, and the page's **Download PDF** button downloads that file. It no longer opens the print dialog. It uses a Chrome, Edge, Brave, or Chromium that is already installed; without one, the button falls back to the print dialog. `--no-pdf` skips it, and `--png` still saves one tall image.

**Unchanged:** the how-it-works flowchart, charts, branding on the page only, no footer or link on comments by default, and the rule that nothing posts without your approval.

### 2.18.0 — 2026-11-17

**Added**
- **A "how it works" flowchart on every page.** With `html`, each PR now gets an overview flowchart that explains how the changed code works, drawn from the code that was read. Each finding is pinned to the step where it applies, as a clickable badge such as `P1 #3`, so you see the problem in the flow, not just in a list.
- **Save as PDF or an image.** The page has a Save as PDF button and a Save PNG button on each flowchart. Ask for a PDF or PNG of the whole review and the skill saves `preview.pdf` or `preview.png` in the run folder, using a Chrome, Edge, Brave, or Chromium that is already installed.

**Changed**
- Tighter flowcharts and charts, a print layout for the PDF, and a warning when a PR has no overview or a badge points at a finding that does not exist.

**Unchanged:** branding is on the HTML page only, comments carry no footer or link by default, flowcharts are never part of a comment, and nothing posts without your approval.

### 2.17.0 — 2026-11-17

**Added**
- **A more visual HTML preview.** With `html`, the page now opens with the AdversaryPR logo, name, and version, and ends with a short AdversaryPR footer. Under the header are two charts: findings by severity, and where the findings are, file by file.
- **Flowcharts.** When a picture makes a problem clearer, such as a retry loop that never ends or a state that is never reset, the page draws a flowchart under that finding. For a PR that adds or reshapes a flow, one overview flowchart shows above its findings. They are drawn from the code that was read, work offline, follow light and dark mode, and print cleanly.
- The page warns when a flowchart cannot be drawn (an edge naming a missing step, too many steps), and the review fixes it before you see the page.

**Unchanged:** the branding is on the HTML page only. Comments still carry no footer or link by default, flowcharts are never part of a comment, and nothing is added to a pull request that you did not write. The checks, the evidence standard, severity, the comment format, the logo banner, `model=`, per-organization tokens, anonymous usage counts, and the rule that nothing posts without your approval are unchanged.

### 2.16.0 — 2026-11-16

**Changed**
- **No footer or link on comments by default.** Comments end with their own text and nothing else: no signature line and no link to a website. Nothing is added to anyone's pull request that you did not write.

**Unchanged:** the checks, the evidence standard, severity, the comment format, the logo banner, the HTML preview, `model=`, per-organization tokens, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.15.0 — 2026-11-16

**Added**
- **A token for each Azure DevOps organization.** `~/.ado-pr-review-creds.json` can now hold several profiles, each for an organization, and optionally one project or repo, so one run can review PRs from different organizations with the right PAT for each. The most specific match wins, and your old single-PAT file keeps working as the fallback. Add one yourself, with the PAT typed hidden so it never shows in the chat: `! python3 ~/.claude/skills/adversary/versions/2.15.0/scripts/creds.py add --org Contoso`. See what is saved (PATs hidden) with `creds.py list`. PATs are never printed, never given to review agents, and the file is owner-only.
- **GitHub accounts by owner.** If the `gh` CLI holds several accounts, you can map an owner to one (`creds.py github-map --owner acme --gh-user alice`), and that PR's calls use that account without switching the active one.

**Unchanged:** the checks, the evidence standard, severity, the comment format, the logo banner, the HTML preview, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.14.0 — 2026-11-16

**Changed**
- **The logo now shows on every run.** The banner is printed first, before the skill reads its instructions or does anything else, so it can't get skipped. If a run somehow reaches the preview without it, the preview prints it.
- **The HTML preview has a clickable link.** With `html`, the chat prints the page's `file://` link on a line of its own, so you can click it in your terminal (or copy it) instead of hunting for the file.

**Unchanged:** the checks, the evidence standard, severity, the comment format, the HTML preview itself, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.13.0 — 2026-11-14

**Changed**
- The sentence "Please take a look at the suggested fix below, unless this was intentional." is back before every fix, as it was before 2.12.0. Everything else from 2.12.0 stays: comments get to the point, are written in plain, gentle words, and don't all open the same way.

**Unchanged:** the checks, the evidence standard, severity, the HTML preview, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.12.0 — 2026-11-14

**Changed**
- **Comments get to the point.** They no longer all open with "I noticed that ..."; it is fine on some comments but never required. A comment says what is wrong, asks the author a short question when only the author can answer it, and suggests a fix or a way forward. When the answer is clear, it skips the question.
- **Gentle and plain.** Fixes are offered as suggestions, not orders. Comments are written at about a 4th-grade reading level: short sentences and everyday words. Code and names stay as they are.
- The fixed sentence "Please take a look at the suggested fix below, unless this was intentional." was dropped here (it returns in 2.13.0). The fix still arrives as a code snippet, and on GitHub as a suggested change when it replaces exactly the lines it points at.

**Unchanged:** the checks, the evidence standard, severity, the HTML preview, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.11.0 — 2026-11-14

**Changed**
- Comment signature handling is tidier.

**Unchanged:** the checks, the comment format, the HTML preview, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

### 2.10.0 — 2026-11-14

**Changed**
- **A bare PR number** (`/adversary 38842`) now reads the organization, project, and repo from the Azure DevOps remote of the folder you are in. With no Azure DevOps remote, it asks for the full PR link. Before, it assumed one fixed repo.
- Examples and wording that named a specific company were replaced with generic ones (Contoso). The checks and the comment format are the same.

**Unchanged:** the rules, the reviewer's approach, the HTML preview, `model=`, anonymous usage counts, and the rule that nothing posts without your approval.

## Releasing a new version

1. Copy the latest `versions/<x>/` folder to `versions/<new>/`, and change only the new folder. Never edit a released folder.
2. Update **Latest version** and the "Available versions" table, and add a release-notes entry (Added / Changed / Fixed / Removed).
3. Update the `description` at the top if the latest version's abilities changed.
4. Repackage the skill and re-upload it to the org. For the local `/adversary`, copy the skill folder to `~/.claude/skills/adversary/`.

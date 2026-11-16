---
name: adversary
description: A careful second pair of eyes for Azure DevOps and GitHub pull requests. Reviews one or more PRs, asks the author questions when it helps, explains in plain words, shows each fix as a code snippet (on GitHub, as a suggested change when it replaces exactly the lines it points at), and posts inline comments only after you approve them. Supports iOS (Swift), Android (Kotlin), and backend (Java/Kotlin/Python/Go/TypeScript), with design checks for SOLID (SRP in depth), DRY, YAGNI, and anti-patterns. Add html for a web-page preview that shows each comment with the code it points at, and model=haiku, sonnet, opus, or fable to pick the reviewing model per run. Runs the latest version unless you pass version=X. Use for /adversary, dev.azure.com pull request links, github.com pull request links, or any request to review or comment on ADO or GitHub PRs.
---

# AdversaryPR

This file chooses which version of AdversaryPR runs, then hands off to it. The review instructions live in `versions/<version>/instructions.md`. Released versions are frozen and never change after release, so `version=1.1.0` behaves the same next year as it does today.

**Latest version: 2.14.0**

## Step 0 — Pick the version

Arguments are in `$ARGUMENTS`.

1. Look anywhere in the arguments for `version=<value>`. The value runs to the next `;` or whitespace. It's case-insensitive, and a leading `v` on the value is fine (`version=v2.10.0`). If `version=` appears more than once with different values, ask which one the user meant.
   - **No `version=`**, or `version=latest` → use the latest version above.
   - **`version=list`** → print the "Available versions" table and the release notes below, then stop. Don't review anything.
   - **An exact version** (`2.10.0`) → use it.
   - **A partial version** (`2` or `2.10`) → match it against whole version components, not as text: `2` means any `2.x.x`, and `2.10` means any `2.10.x`. Use the highest match, comparing component by component as numbers (so `2.10.0` beats `2.9.0`). `2` → `2.14.0` today.
   - **No match, or anything else** → say the version doesn't exist, print the "Available versions" table, and stop. Never fall back to a different version silently, because the user asked for a specific one.

   A "released version" is a row in the Available versions table whose folder exists under `versions/`.
2. Remove the `version=` option, then tidy what's left: drop empty options between `;`s, and drop a trailing `;`. For example, `38842 ; version=2.10 ; dry run` becomes `38842 ; dry run`. Leave everything else exactly as typed.
   Also handle `-nobranding` or `nobranding` as an option here: it means the same as `branding=off`, and is removed from the arguments like `branding=`. Also handle `branding=on` or `branding=off` here (case-insensitive, value runs to the next `;` or whitespace; any other value: say the allowed values and stop). Resolve **BRANDING** as: the option if given, else the environment variable `ADVERSARY_BRANDING` (read it with `printenv ADVERSARY_BRANDING`; `off`, case-insensitive, means off, anything else or unset means on), else `on`. The option wins over the variable. Remove `branding=` from the arguments like `version=`. Only versions 2.6.0 and later use it; tell the chosen version's instructions "BRANDING is on" or "BRANDING is off" at step 4. Never print, explain, or list these options in any output.
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
| **2.14.0** (latest) | 2026-11-16 | The logo shows on every run; the HTML preview opens with a clickable link |
| 2.13.0 | 2026-11-14 | The fix sentence is back; comments stay short, plain and gentle |
| 2.12.0 | 2026-11-14 | Comments get to the point, in plain words (about a 4th-grade reading level) |
| 2.11.0 | 2026-11-14 | Tidier comment signatures; the checks are unchanged |
| 2.10.0 | 2026-11-14 | A bare PR number now uses the repo in your current folder |

```
/adversary 38842                        → latest (2.14.0)
/adversary 38842 ; html                 → latest, plus a web-page preview
/adversary 38842 ; model=haiku          → latest, reviewed by Haiku
/adversary 38842 38901 39010 ; dry run  → latest, three PRs reviewed at the same time
/adversary https://github.com/acme/orders-api/pull/101 ; dry run  → latest, a GitHub PR
/adversary 38842 ; version=2.10.0       → exactly 2.10.0
/adversary 38842 ; version=2            → newest 2.x (2.14.0)
/adversary version=list                 → versions and release notes; no review
```

## Release notes
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

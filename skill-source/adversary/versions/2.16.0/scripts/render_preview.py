#!/usr/bin/env python3
"""Render a AdversaryPR run folder as one self-contained HTML preview page.

Usage:
    python3 render_preview.py RUN_DIR [PR_ID ...] [--version X.Y.Z]

Reads RUN_DIR/PR-<id>/{pr.json, findings.json, diff.patch} (pr.json's "provider"
is "ado", the default, or "github") and writes
RUN_DIR/preview.html. PR_IDs set the order of the PRs on the page; without
them, every PR-* folder is shown in ascending PR number order.

The page shows each finding's comment exactly as findings.json holds it (the
same text Step 6 posts), the diff lines it points at, and a picker that builds
the selection reply to type back into the chat. Nothing on the page can post
anything: it loads no network resources and calls no APIs.

A finding may have "startLine" (first line of a multi-line anchor; "line" is the
last). Every line of the range must be an added or context line of one hunk.
Fenced blocks render as code; a ```suggestion block gets a "Suggested change"
label. WARNING lines flag a suggestion block on an Azure DevOps PR or without a
valid anchor, alongside the older placement checks.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SEVERITIES = ["P1", "P2", "P3", "P4", "P5"]
CONTEXT_LINES = 4  # diff lines shown above and below the commented line
WORK_ITEM_REF = re.compile(r"(^|[\s(\[])#(\d+)\b")
PLATFORM = {"ado": "Azure DevOps", "github": "GitHub"}


def platform_of(meta) -> str:
    """'github' when pr.json says so, otherwise 'ado' (older runs have no provider)."""
    prov = str((meta or {}).get("provider") or "ado").strip().lower()
    return "github" if prov == "github" else "ado"


# ---------------------------------------------------------------- markdown --
# A small renderer for the markdown AdversaryPR comments use: paragraphs,
# headings, bullet and numbered lists, block quotes, fenced code, inline code,
# bold, italics, and links. Everything is HTML-escaped before any markup is
# added, because PR text is untrusted.

def _inline(text: str, warnings: list) -> str:
    # Swap code spans for placeholders first, so emphasis can wrap them
    # (**title with `code`**) but nothing inside them is formatted.
    spans = []

    def stash(m):
        spans.append("<code>" + html.escape(m.group(2).strip()) + "</code>")
        return "\x00%d\x00" % (len(spans) - 1)

    s = _inline_text(re.sub(r"(`+)(.+?)\1", stash, text.replace("\x00", "")), warnings)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], s)


def _inline_text(text: str, warnings: list) -> str:
    s = html.escape(text, quote=False)
    # Links: only http(s) targets become anchors. The anchor is stashed so the
    # emphasis rules below cannot touch the URL (underscores, asterisks).
    anchors = []

    def link(m):
        anchors.append(
            '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
            % (m.group(2).replace('"', "%22"), m.group(1))
        )
        return "\x01%d\x01" % (len(anchors) - 1)

    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", link, s.replace("\x01", ""))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w])__(.+?)__(?![\w])", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w])_(?![\s_])(.+?)(?<![\s_])_(?![\w])", r"<em>\1</em>", s)

    def mark_ref(m):
        warnings.append("#" + m.group(2))
        return (
            m.group(1)
            + '<span class="wi" title="This platform turns #number into a link">#'
            + m.group(2)
            + "</span>"
        )

    s = WORK_ITEM_REF.sub(mark_ref, s)
    return re.sub(r"\x01(\d+)\x01", lambda m: anchors[int(m.group(1))], s)


def render_fence(lang: str, body: list) -> str:
    """A fenced block. `suggestion` gets a "Suggested change" label and a green
    look (GitHub shows the block as the replacement lines); `diff` colors its
    + and - lines; anything else is a plain code block tagged with its language."""
    kind = lang.lower()
    if kind == "suggestion":
        rows = "".join('<span class="dl add">%s</span>' % (html.escape(l) or "&nbsp;") for l in body)
        return (
            '<div class="suggest"><div class="suggest-label">Suggested change</div>'
            "<pre><code class=\"lang-suggestion\">%s</code></pre></div>" % rows
        )
    if kind == "diff":
        def row(l):
            cls = "add" if l.startswith("+") and not l.startswith("+++") else (
                "del" if l.startswith("-") and not l.startswith("---") else "ctx")
            return '<span class="dl %s">%s</span>' % (cls, html.escape(l) or "&nbsp;")
        return '<pre><code class="lang-diff">%s</code></pre>' % "".join(row(l) for l in body)
    cls = ' class="lang-%s"' % html.escape(lang) if lang else ""
    return "<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(body)))


SUGGESTION_FENCE = re.compile(r"^[ \t]*(```+|~~~+)[ \t]*suggestion\b", re.IGNORECASE | re.MULTILINE)


def has_suggestion_block(content: str) -> bool:
    return bool(SUGGESTION_FENCE.search(str(content or "").replace("\r\n", "\n")))


def render_markdown(text: str, warnings: list) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out, para = [], []

    def flush():
        if para:
            out.append("<p>" + _inline(" ".join(l.strip() for l in para), warnings) + "</p>")
            para.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        fence = re.match(r"^\s*(```+|~~~+)\s*([\w+#.-]*)", line)
        if fence:
            flush()
            marker, lang = fence.group(1), fence.group(2)
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(marker):
                body.append(lines[i])
                i += 1
            out.append(render_fence(lang, body))
            i += 1
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, _inline(heading.group(2), warnings), level))
            i += 1
            continue
        if re.match(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$", line):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if re.match(r"^\s*>", line):
            flush()
            quote = []
            while i < len(lines) and re.match(r"^\s*>", lines[i]):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + render_markdown("\n".join(quote), warnings) + "</blockquote>")
            continue
        item = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", line)
        if item:
            flush()
            ordered = item.group(1)[0].isdigit()
            items = []
            while i < len(lines):
                m = re.match(r"^\s*([-*+]|\d+[.)])\s+(.*)$", lines[i])
                if m:
                    items.append([m.group(2)])
                elif lines[i].strip() and lines[i].startswith((" ", "\t")) and items:
                    items[-1].append(lines[i].strip())
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(
                "<%s>%s</%s>"
                % (tag, "".join("<li>" + _inline(" ".join(it), warnings) + "</li>" for it in items), tag)
            )
            continue
        para.append(line)
        i += 1
    flush()
    return "\n".join(out)


# -------------------------------------------------------------------- diff --

def _norm(path: str) -> str:
    path = path.strip().split("\t")[0]
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path.lstrip("/")


def parse_diff(text: str) -> dict:
    """Map each new-file path to its hunks: lists of (kind, old_no, new_no, text)."""
    files = {}
    current = None
    hunk = None
    old_left = new_left = 0
    old_no = new_no = 0
    for raw in text.split("\n"):
        if hunk is not None and (old_left > 0 or new_left > 0):
            if raw.startswith("\\"):
                continue
            kind = raw[:1] if raw[:1] in "+- " else " "
            body = raw[1:]
            if kind == "+":
                hunk.append(("+", None, new_no, body))
                new_no += 1
                new_left -= 1
            elif kind == "-":
                hunk.append(("-", old_no, None, body))
                old_no += 1
                old_left -= 1
            else:
                hunk.append((" ", old_no, new_no, body))
                old_no += 1
                new_no += 1
                old_left -= 1
                new_left -= 1
            continue
        if raw.startswith("+++ "):
            target = raw[4:]
            current = None if target.strip() == "/dev/null" else _norm(target)
            if current is not None:
                files.setdefault(current, [])
            hunk = None
            continue
        header = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", raw)
        if header and current is not None:
            old_no, new_no = int(header.group(1)), int(header.group(3))
            old_left = int(header.group(2)) if header.group(2) is not None else 1
            new_left = int(header.group(4)) if header.group(4) is not None else 1
            hunk = []
            files[current].append(hunk)
    return files


def find_file(files: dict, file_path: str):
    want = _norm(file_path)
    if want in files:
        return want
    matches = [p for p in files if p.endswith("/" + want) or want.endswith("/" + p)]
    return matches[0] if len(matches) == 1 else None


def snippet(files: dict, file_path: str, line: int, start_line=None):
    """Return (rows, problem). rows is None when the anchor can't be placed.

    The anchor is `start_line`..`line` (just `line` when start_line is None).
    Every line of it must be an added or context line of one hunk. rows are
    (diff row, highlighted) pairs, with the whole range highlighted.
    """
    first = line if start_line is None else start_line
    if first > line:
        return None, "startLine %d is after line %d" % (first, line)
    path = find_file(files, file_path)
    if path is None:
        return None, "%s is not in this PR's diff" % file_path
    span = "line %d" % line if first == line else "lines %d-%d" % (first, line)
    for hunk in files[path]:
        pos = {}
        for idx, (kind, _old, new, _body) in enumerate(hunk):
            if kind != "-" and new is not None:
                pos[new] = idx
        if line in pos or first in pos:
            missing = [n for n in range(first, line + 1) if n not in pos]
            if missing:
                return None, "%s is not all added or context lines of one hunk of %s (line %d is not)" % (
                    span, file_path, missing[0])
            lo_i, hi_i = pos[first], pos[line]
            if first != line and any(hunk[k][0] == "-" for k in range(lo_i, hi_i + 1)):
                return None, "%s spans removed lines in %s; a range must be added or context lines only" % (
                    span, file_path)
            lo, hi = max(0, lo_i - CONTEXT_LINES), min(len(hunk), hi_i + CONTEXT_LINES + 1)
            return [(r, lo_i <= j <= hi_i) for j, r in enumerate(hunk[lo:hi], start=lo)], None
    if first != line:
        return None, "%s is not all added or context lines of one hunk of %s" % (span, file_path)
    return None, "line %d is not an added or context line of %s in this PR's diff" % (line, file_path)


# -------------------------------------------------------------------- page --

def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except (ValueError, OSError) as exc:
        return None, "unreadable (%s)" % exc


def collect(run_dir: Path, order: list) -> list:
    if order:
        folders = [run_dir / ("PR-%s" % pr) for pr in order]
    else:
        def key(p):
            num = p.name[3:]
            return (0, int(num), "") if num.isdigit() else (1, 0, num)
        folders = sorted((p for p in run_dir.glob("PR-*") if p.is_dir()), key=key)
    prs = []
    for folder in folders:
        pr_id = folder.name[3:]
        meta, meta_err = load_json(folder / "pr.json")
        found, found_err = load_json(folder / "findings.json")
        try:
            diff_text = (folder / "diff.patch").read_text(encoding="utf-8", errors="replace")
        except OSError:
            diff_text = ""
        meta = meta or {}
        status = "ok"
        if meta.get("error"):
            status = "failed: %s" % meta["error"]
        elif meta_err:
            status = "failed: pr.json %s" % meta_err
        elif found_err:
            status = "review failed: findings.json %s" % found_err
        elif found and found.get("status") not in (None, "ok"):
            status = str(found.get("status"))
        prs.append(
            {
                "id": pr_id,
                "meta": meta,
                "findings": (found or {}).get("findings") or [],
                "heldBack": (found or {}).get("heldBack") or [],
                "skippedExisting": (found or {}).get("skippedExisting") or 0,
                "status": status,
                "files": parse_diff(diff_text),
            }
        )
    return prs


def render_snippet(rows) -> str:
    out = ['<table class="diff">']
    for (kind, old, new, body), is_target in rows:
        cls = {"+": "add", "-": "del", " ": "ctx"}[kind]
        if is_target:
            cls += " target"
        out.append(
            '<tr class="%s"><td class="ln">%s</td><td class="ln">%s</td><td class="mk">%s</td>'
            '<td class="src">%s</td></tr>'
            % (cls, esc(old or ""), esc(new or ""), esc(kind.strip()), esc(body) or "&nbsp;")
        )
    out.append("</table>")
    return "".join(out)


def render_finding(pr: dict, f: dict, multi: bool, problems: list) -> str:
    n = f.get("n")
    ref = "%s#%s" % (pr["id"], n) if multi else "#%s" % n
    sev = str(f.get("severity", "")).upper()
    sev_cls = sev.lower() if sev in SEVERITIES else "px"
    file_path, line = f.get("filePath", ""), f.get("line")
    start = f.get("startLine")
    refs = []
    body = render_markdown(str(f.get("content", "")), refs)

    notes = []
    try:
        line_no = int(line)
    except (TypeError, ValueError):
        line_no = None
    start_no = None
    if start is not None:
        try:
            start_no = int(start)
        except (TypeError, ValueError):
            start_no = None
    if line_no is None:
        rows, problem = None, "line is missing or not a number"
    elif start is not None and start_no is None:
        rows, problem = None, "startLine is not a number"
    else:
        rows, problem = snippet(pr["files"], file_path, line_no, start_no)
    if problem:
        notes.append(problem)
        problems.append("%s: %s" % (ref, problem))
    provider = platform_of(pr["meta"])
    platform = PLATFORM[provider]
    if provider == "github":
        if str(file_path).startswith("/"):
            notes.append("filePath must not start with / on GitHub")
            problems.append("%s: filePath %r must not start with / on GitHub" % (ref, file_path))
    elif not str(file_path).startswith("/"):
        notes.append("filePath must start with /")
        problems.append("%s: filePath %r must start with /" % (ref, file_path))
    content = str(f.get("content", ""))
    suggests = has_suggestion_block(content)
    if suggests and provider == "ado":
        msg = "a suggestion block will not show a Commit button on Azure DevOps; use a language or diff block"
        notes.append(msg)
        problems.append("%s: %s" % (ref, msg))
    if suggests and rows is None:
        msg = "a suggestion block needs a valid anchor: line (and startLine) must be added or context lines of one hunk"
        notes.append(msg)
        problems.append("%s: %s" % (ref, msg))
    if suggests and provider == "github" and f.get("suggestion") is not True:
        msg = 'a suggestion block is present but the finding does not have "suggestion": true'
        notes.append(msg)
        problems.append("%s: %s" % (ref, msg))
    if f.get("suggestion") is True and not suggests:
        msg = '"suggestion": true but the comment has no suggestion block'
        notes.append(msg)
        problems.append("%s: %s" % (ref, msg))
    if refs:
        kind = "an issue or pull request link" if provider == "github" else "a work-item link"
        msg = "%s will become %s in %s; refer to file and line instead" % (
            ", ".join(sorted(set(refs))), kind, platform)
        notes.append(msg)
        problems.append("%s: %s" % (ref, msg))

    if start_no is not None and line_no is not None and start_no != line_no:
        where = "lines %s-%s" % (start_no, line_no)
    else:
        where = "line %s" % line
    code = render_snippet(rows) if rows else '<p class="nodiff">No diff lines to show.</p>'
    warn = "".join('<p class="warn">&#9888; %s</p>' % esc(n_) for n_ in notes)
    return (
        '<article class="finding" id="f-{pid}-{n}">'
        '<header><label class="pick-wrap"><input type="checkbox" class="pick" data-n="{n}" checked> '
        '<span class="ref">{ref}</span></label>'
        '<span class="sev {sevc}">{sev}</span><span class="summary">{summary}</span></header>'
        '<p class="where"><code>{path}</code> {where} &middot; {rule}</p>'
        "{warn}{code}"
        '<div class="comment"><div class="comment-label">Comment, as {platform} will show it</div>{body}</div>'
        '<details class="raw"><summary>Exact text that will be posted</summary><pre>{raw}</pre></details>'
        "</article>"
    ).format(
        platform=esc(platform),
        pid=esc(pr["id"]),
        n=esc(n),
        ref=esc(ref),
        sevc=sev_cls,
        sev=esc(sev),
        summary=esc(f.get("summary", "")),
        path=esc(file_path),
        where=esc(where),
        rule=esc(f.get("ruleSet", "")),
        warn=warn,
        code=code,
        body=body,
        raw=esc(f.get("content", "")),
    )


def counts(findings: list) -> dict:
    c = {s: 0 for s in SEVERITIES}
    for f in findings:
        s = str(f.get("severity", "")).upper()
        if s in c:
            c[s] += 1
    return c


def pr_label(meta: dict, pr_id) -> str:
    if platform_of(meta) == "github" and meta.get("owner") and meta.get("repo"):
        return "%s/%s#%s (%s)" % (meta["owner"], meta["repo"], meta.get("prId", pr_id), pr_id)
    return "PR %s" % pr_id


def render_pr(pr: dict, multi: bool, problems: list) -> str:
    meta = pr["meta"]
    title = meta.get("title") or "(no title)"
    url = meta.get("url") or ""
    provider = platform_of(meta)
    link = (
        '<a href="%s" target="_blank" rel="noopener noreferrer">Open in %s</a>' % (esc(url), PLATFORM[provider])
        if str(url).startswith("https://")
        else ""
    )
    branch = ""
    if meta.get("sourceBranch") or meta.get("targetBranch"):
        branch = "<code>%s</code> &rarr; <code>%s</code>" % (
            esc(meta.get("sourceBranch", "?")),
            esc(meta.get("targetBranch", "?")),
        )
    conv = meta.get("conventions") or []
    conv_line = "Repo conventions read: %s" % esc(", ".join(conv)) if conv else "No repo convention files found"
    parts = [
        '<section class="pr" data-pr="%s" id="pr-%s">' % (esc(pr["id"]), esc(pr["id"])),
        "<h2>%s &middot; %s</h2>" % (esc(pr_label(meta, pr["id"])), esc(title)),
        '<p class="meta">%s</p>' % " &middot; ".join(x for x in [branch, link, conv_line] if x),
    ]
    if pr["status"] != "ok":
        parts.append('<p class="warn">&#9888; %s</p>' % esc(pr["status"]))
    findings = sorted(
        pr["findings"],
        key=lambda f: (
            SEVERITIES.index(str(f.get("severity", "")).upper())
            if str(f.get("severity", "")).upper() in SEVERITIES
            else 9,
            f.get("n") or 0,
        ),
    )
    if findings:
        rows = "".join(
            '<tr><td><a href="#f-{pid}-{n}">{n}</a></td><td><span class="sev {sc}">{s}</span></td>'
            "<td><code>{file}</code></td><td>{line}</td><td>{summary}</td></tr>".format(
                pid=esc(pr["id"]),
                n=esc(f.get("n")),
                sc=str(f.get("severity", "")).lower(),
                s=esc(f.get("severity")),
                file=esc(str(f.get("filePath", "")).rsplit("/", 1)[-1]),
                line=esc(
                    "%s-%s" % (f.get("startLine"), f.get("line"))
                    if f.get("startLine") not in (None, f.get("line"))
                    else f.get("line")
                ),
                summary=esc(f.get("summary")),
            )
            for f in findings
        )
        parts.append(
            '<table class="index"><thead><tr><th>#</th><th>Sev</th><th>File</th><th>Line</th>'
            "<th>Summary</th></tr></thead><tbody>%s</tbody></table>" % rows
        )
        parts.extend(render_finding(pr, f, multi, problems) for f in findings)
    elif pr["status"] == "ok":
        parts.append('<p class="empty">No findings for this PR.</p>')
    extra = []
    if pr["heldBack"]:
        extra.append(
            "<details><summary>Considered and dropped (%d)</summary><ul>%s</ul></details>"
            % (len(pr["heldBack"]), "".join("<li>%s</li>" % esc(h) for h in pr["heldBack"]))
        )
    if pr["skippedExisting"]:
        extra.append(
            '<p class="meta">%s finding(s) skipped because an existing thread already covers them.</p>'
            % esc(pr["skippedExisting"])
        )
    parts.extend(extra)
    parts.append("</section>")
    return "\n".join(parts)


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--fg:#1d2330;--muted:#5b6474;--line:#dde1e8;--code:#f0f2f5;
--add:#e6f6ea;--add-mk:#1f7a3a;--del:#fdecec;--del-mk:#b42318;--target:#fff4c2;--target-edge:#d4a106;
--p1:#b42318;--p2:#c4560c;--p3:#2f5fb3;--p4:#6b47b8;--p5:#5b6474;--warn-bg:#fff6e0;--warn-fg:#7a4b00;--accent:#2f5fb3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171c;--card:#1c2027;--fg:#e4e7ec;
--muted:#9aa3b2;--line:#323844;--code:#262b33;--add:#173323;--add-mk:#6fd08c;--del:#3a1d1d;--del-mk:#ff8a80;
--target:#3d3517;--target-edge:#e0b43a;--p1:#ff6b5e;--p2:#ff9d4d;--p3:#7aa7ff;--p4:#b79cff;--p5:#9aa3b2;
--warn-bg:#3a2f12;--warn-fg:#f5d48a;--accent:#7aa7ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 140px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 4px}
.meta,.lede{color:var(--muted);margin:4px 0}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
table.index,table.summary{width:100%;border-collapse:collapse;margin:12px 0;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
table.index th,table.index td,table.summary th,table.summary td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
table.summary td.num,table.summary th.num{text-align:center}
.finding{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:16px 0}
.finding header{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pick-wrap{display:flex;gap:6px;align-items:center;font-weight:600;cursor:pointer}
.pick{width:18px;height:18px}
.finding.off{opacity:.55}
.summary{font-weight:600}
.sev{display:inline-block;min-width:30px;text-align:center;font-weight:700;font-size:12px;padding:1px 6px;border-radius:4px;color:#fff}
.sev.p1{background:var(--p1)}.sev.p2{background:var(--p2)}.sev.p3{background:var(--p3)}.sev.p4{background:var(--p4)}.sev.p5{background:var(--p5)}
.where{color:var(--muted);margin:6px 0 10px;word-break:break-all}
table.diff{width:100%;border-collapse:collapse;background:var(--code);border-radius:6px;overflow:hidden;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;table-layout:fixed}
table.diff td{padding:1px 6px;white-space:pre-wrap;word-break:break-word}
table.diff td.ln{width:44px;color:var(--muted);text-align:right;user-select:none}
table.diff td.mk{width:16px;user-select:none}
tr.add{background:var(--add)}tr.add td.mk{color:var(--add-mk)}
tr.del{background:var(--del)}tr.del td.mk{color:var(--del-mk)}
tr.target{background:var(--target);box-shadow:inset 4px 0 0 var(--target-edge)}
.comment{border-left:3px solid var(--accent);padding:4px 0 4px 14px;margin:14px 0 6px}
.comment-label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.comment pre{background:var(--code);padding:10px;border-radius:6px;overflow-x:auto}
.comment code{background:var(--code);padding:1px 4px;border-radius:3px}
.comment pre code{background:none;padding:0}
.dl{display:block;white-space:pre}
.dl.add{background:var(--add)}.dl.del{background:var(--del)}
.suggest{border:1px solid var(--add-mk);border-radius:6px;margin:8px 0;overflow:hidden}
.suggest-label{background:var(--add);color:var(--add-mk);font-size:12px;font-weight:600;padding:3px 10px}
.suggest pre{margin:0;border-radius:0}
.suggest .dl.add::before{content:"+ ";color:var(--add-mk)}
.comment blockquote{margin:6px 0;padding-left:10px;border-left:3px solid var(--line);color:var(--muted)}
.raw summary{cursor:pointer;color:var(--muted);font-size:13px}
.raw pre{white-space:pre-wrap;word-break:break-word;background:var(--code);padding:10px;border-radius:6px}
.warn{background:var(--warn-bg);color:var(--warn-fg);padding:6px 10px;border-radius:6px;margin:8px 0}
.wi{background:var(--warn-bg);color:var(--warn-fg);border-radius:3px;padding:0 2px}
.empty,.nodiff{color:var(--muted)}
a{color:var(--accent)}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px;box-shadow:0 -4px 16px rgba(0,0,0,.08)}
.bar-inner{max-width:1000px;margin:0 auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.bar input[type=text]{flex:1 1 260px;min-width:0;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.bar button{padding:8px 12px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);cursor:pointer;font:inherit}
.bar button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.bar .count{color:var(--muted);font-size:13px}
"""

JS = r"""
(function(){
  var sections=[].slice.call(document.querySelectorAll('section.pr'));
  var multi=sections.length>1;
  var out=document.getElementById('reply'), count=document.getElementById('count');
  function ranges(ns){
    var parts=[],i=0;
    while(i<ns.length){var j=i;while(j+1<ns.length&&ns[j+1]===ns[j]+1)j++;
      parts.push(j-i>=2?ns[i]+'-'+ns[j]:(j>i?ns[i]+' '+ns[j]:''+ns[i]));i=j+1;}
    return parts.join(' ');
  }
  function update(){
    var per=[],picked=0,total=0;
    sections.forEach(function(s){
      var boxes=[].slice.call(s.querySelectorAll('input.pick'));
      if(!boxes.length)return;
      var sel=[],off=[];
      boxes.forEach(function(b){var n=+b.dataset.n;(b.checked?sel:off).push(n);
        b.closest('.finding').classList.toggle('off',!b.checked);});
      sel.sort(function(a,b){return a-b});off.sort(function(a,b){return a-b});
      per.push({id:s.dataset.pr,sel:sel,off:off});picked+=sel.length;total+=boxes.length;
    });
    var reply;
    if(!total||!picked)reply='none';
    else if(picked===total)reply='all';
    else if(!multi){var p=per[0],a=ranges(p.sel),b='all except '+p.off.join(' ');reply=a.length<=b.length?a:b;}
    else{
      var byPr=per.filter(function(p){return p.sel.length}).map(function(p){
        return p.id+': '+(p.off.length?ranges(p.sel):'all');}).join(' ; ');
      var offs=[];per.forEach(function(p){p.off.forEach(function(n){offs.push(p.id+'#'+n)})});
      var exc='all except '+offs.join(' ');
      reply=exc.length<byPr.length?exc:byPr;
    }
    out.value=reply;
    count.textContent=picked+' of '+total+' selected';
  }
  document.addEventListener('change',function(e){if(e.target.classList.contains('pick'))update();});
  function setAll(v){[].slice.call(document.querySelectorAll('input.pick')).forEach(function(b){b.checked=v});update();}
  document.getElementById('all').onclick=function(){setAll(true)};
  document.getElementById('none').onclick=function(){setAll(false)};
  document.getElementById('copy').onclick=function(){
    var btn=this;function done(){btn.textContent='Copied';setTimeout(function(){btn.textContent='Copy reply'},1500);}
    if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(out.value).then(done,function(){out.select();document.execCommand('copy');done();});}
    else{out.select();document.execCommand('copy');done();}
  };
  update();
})();
"""


def render_page(prs: list, version: str, run_dir: Path, problems: list) -> str:
    multi = len(prs) > 1
    total = sum(len(p["findings"]) for p in prs)
    body = []
    if multi:
        rows = []
        for pr in prs:
            c = counts(pr["findings"])
            cells = "".join(
                '<td class="num">%s</td>' % (c[s] if pr["status"] == "ok" else "&mdash;") for s in SEVERITIES
            )
            rows.append(
                '<tr><td><a href="#pr-{id}">{id}</a></td><td>{title}</td>{cells}<td>{status}</td></tr>'.format(
                    id=esc(pr["id"]), title=esc(pr["meta"].get("title", "")), cells=cells, status=esc(pr["status"])
                )
            )
        body.append(
            '<table class="summary"><thead><tr><th>PR</th><th>Title</th>%s<th>Status</th></tr></thead>'
            "<tbody>%s</tbody></table>"
            % ("".join('<th class="num">%s</th>' % s for s in SEVERITIES), "".join(rows))
        )
    body.extend(render_pr(pr, multi, problems) for pr in prs)
    heading = "%d PRs, %d findings" % (len(prs), total) if multi else "PR %s, %d findings" % (
        prs[0]["id"] if prs else "?",
        total,
    )
    plats = sorted({PLATFORM[platform_of(p["meta"])] for p in prs})
    if plats:
        heading += " (%s)" % " + ".join(plats)
    hint = (
        "Per PR: <code>38842: 1 3-5 ; 38901: all</code>. PRs you leave out post nothing."
        if multi
        else "Numbers, ranges, <code>all</code>, <code>all except 2 4</code>, or <code>none</code>."
    )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>AdversaryPR preview</title>
<style>{css}</style></head>
<body><main>
<h1>AdversaryPR v{version} &middot; {heading}</h1>
<p class="lede">Generated {when}. Nothing is posted from this page. Untick what you don't want, then copy the reply at the bottom into Claude. {hint}</p>
<p class="meta">Run folder: <code>{run_dir}</code></p>
{body}
</main>
<div class="bar"><div class="bar-inner">
<span class="count" id="count"></span>
<input type="text" id="reply" readonly aria-label="Reply to type into Claude">
<button id="copy" class="primary">Copy reply</button>
<button id="all">Select all</button><button id="none">Select none</button>
</div></div>
<script>{js}</script>
</body></html>
""".format(
        css=CSS,
        version=esc(version),
        heading=esc(heading),
        when=esc(datetime.now().strftime("%Y-%m-%d %H:%M")),
        hint=hint,
        run_dir=esc(run_dir),
        body="\n".join(body),
        js=JS,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a AdversaryPR run folder as an HTML preview.")
    ap.add_argument("run_dir", help="the run's RUN_DIR")
    ap.add_argument("pr_ids", nargs="*", help="PR numbers, in the order to show them (default: all, ascending)")
    ap.add_argument("--version", default="?", help="AdversaryPR version, for the page heading")
    args = ap.parse_args(argv)

    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        print("error: %s is not a folder" % run_dir, file=sys.stderr)
        return 2
    prs = collect(run_dir, args.pr_ids)
    if not prs:
        print("error: no PR-* folders in %s" % run_dir, file=sys.stderr)
        return 2
    problems = []
    page = render_page(prs, args.version, run_dir, problems)
    out = run_dir / "preview.html"
    out.write_text(page, encoding="utf-8")

    print(out)
    print(out.resolve().as_uri())
    print("%d PR(s), %d finding(s)" % (len(prs), sum(len(p["findings"]) for p in prs)))
    for pr in prs:
        if pr["status"] != "ok":
            print("PR %s: %s" % (pr["id"], pr["status"]))
    for p in problems:
        print("WARNING " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

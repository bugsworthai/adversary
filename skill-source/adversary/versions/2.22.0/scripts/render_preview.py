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

Visual extras (2.17.0): a branded header and footer, a severity chart, a
per-file bar chart, and flowcharts drawn as inline SVG. A finding may carry
"flow", and findings.json may carry a PR-level "overview" flow:
    {"title": "...", "nodes": [{"id": "a", "text": "...", "kind": "start|step|decision|bad|ok"}],
     "edges": [["a", "b"], ["b", "c", "label"]]}
A flow node may carry "findings": [3, 5], the numbers of findings that sit on that
step; the page pins a clickable badge (P1 #3) on the node. Every PR should have an
overview (the page warns when it is missing). Flows are for the page only: they are
never part of a comment's "content".

Fit and impact (2.22.0): pr.json may carry "freshness" (does the PR still fit its target
branch) and findings.json may carry "impact" (a 1-5 judgment of how much of the codebase
the change touches). Both show under the PR heading. The page warns when impact is missing.
--text prints each PR's fit, impact and overview flowchart as plain text for the chat and
writes no files.

Export: the script also saves RUN_DIR/preview.pdf next to the page, using a Chrome,
Edge, Brave or Chromium that is already installed, and the page's Download PDF button
downloads that file (no print dialog). Without such a browser the button opens the
print dialog instead. --no-pdf skips it; --pdf PATH saves the PDF elsewhere; --png
[PATH] saves one tall image. Each flowchart has a Save PNG button.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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



# ------------------------------------------------------------------ visual --

HELMET = "M108.428 12C118.596 12.0001 127.97 17.4985 132.933 26.374L173.817 99.502C181.084 112.5 164.777 125.803 153.504 116.072C148.696 111.922 141.625 111.748 136.618 115.656L120.801 128.004C114.177 133.175 106.604 135.268 99.3145 134.887C91.7178 135.524 83.7496 133.484 76.8193 128.073L61.002 115.726C55.9951 111.817 48.9235 111.991 44.1152 116.142C32.8427 125.871 16.5361 112.57 23.8027 99.5723L64.6875 26.4443C69.6498 17.5688 79.0238 12.0695 89.1924 12.0693H96.7764C97.2681 12.0693 97.7578 12.0819 98.2441 12.1035C99.1013 12.0355 99.9681 12 100.843 12H108.428ZM74.9297 62.3467C75.01 62.356 86.5677 63.7004 89.2334 68.4424C91.9051 73.1949 99.3173 119.413 99.3359 119.529C99.3482 119.468 108.888 71.875 110.503 68.4424C112.114 65.0179 123.674 62.3627 123.743 62.3467H74.9297Z"
MAX_NODES = 14
KINDS = ("start", "step", "decision", "bad", "ok", "note")
NODE_W, LINE_H, GAP_X, GAP_Y, PAD = 176, 17, 40, 38, 18


def logo_svg(size: int = 34) -> str:
    return (
        '<svg class="logo" width="%d" height="%d" viewBox="14 10 172 128" role="img" aria-label="AdversaryPR logo">'
        '<path d="%s" fill="currentColor"/></svg>' % (size * 172 // 128, size, HELMET)
    )


def wrap(text: str, width: int) -> list:
    lines, cur = [], ""
    for word in str(text).split():
        while len(word) > width:
            if cur:
                lines.append(cur)
                cur = ""
            cut = max(word.rfind(".", 1, width), word.rfind("(", 1, width)) + 1 or width
            lines.append(word[:cut])
            word = word[cut:]
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(cur)
    return lines[:5] or [""]


def check_flow(flow, where: str, problems: list, finding_sev=None):
    """Return a cleaned flow dict, or None (with a WARNING) when it cannot be drawn."""
    if flow in (None, "", {}):
        return None
    if not isinstance(flow, dict) or not isinstance(flow.get("nodes"), list) or not flow["nodes"]:
        problems.append("%s: flow needs a non-empty nodes list" % where)
        return None
    nodes, seen = [], set()
    for nd in flow["nodes"]:
        if not isinstance(nd, dict) or not str(nd.get("id", "")).strip() or not str(nd.get("text", "")).strip():
            problems.append("%s: every flow node needs an id and text" % where)
            return None
        nid = str(nd["id"])
        if nid in seen:
            problems.append("%s: flow node id %r is used twice" % (where, nid))
            return None
        seen.add(nid)
        kind = str(nd.get("kind", "step")).lower()
        pins = []
        for n_ in nd.get("findings") or []:
            try:
                n_ = int(n_)
            except (TypeError, ValueError):
                n_ = None
            if finding_sev is not None and n_ in finding_sev:
                pins.append(n_)
            else:
                problems.append("%s: node %r points at finding %r, which does not exist" % (where, nid, n_))
        nodes.append({"id": nid, "text": str(nd["text"]), "kind": kind if kind in KINDS else "step", "pins": pins})
    if len(nodes) > MAX_NODES:
        problems.append("%s: flow has %d nodes; keep it to %d or fewer" % (where, len(nodes), MAX_NODES))
        return None
    edges = []
    for e in flow.get("edges") or []:
        if not isinstance(e, (list, tuple)) or len(e) < 2 or str(e[0]) not in seen or str(e[1]) not in seen:
            problems.append("%s: a flow edge names a node that is not in nodes" % where)
            return None
        edges.append((str(e[0]), str(e[1]), str(e[2]) if len(e) > 2 and e[2] is not None else ""))
    return {"title": str(flow.get("title") or ""), "nodes": nodes, "edges": edges}


def _layers(nodes: list, edges: list):
    """Longest-path layers over the forward edges. DFS marks back edges (loops) so they don't recurse."""
    ids = [n["id"] for n in nodes]
    out = {i: [] for i in ids}
    for a, b, _l in edges:
        out[a].append(b)
    state, back = {}, set()

    def visit(u):
        state[u] = 1
        for v in out[u]:
            if state.get(v) == 1:
                back.add((u, v))
            elif v not in state:
                visit(v)
        state[u] = 2

    incoming = {b for a, b, _ in edges if a != b}
    for i in ids:
        if i not in incoming and i not in state:
            visit(i)
    for i in ids:
        if i not in state:
            visit(i)
    layer = {i: 0 for i in ids}
    for _ in range(len(ids)):
        changed = False
        for a, b, _l in edges:
            if (a, b) in back or a == b:
                continue
            if layer[b] < layer[a] + 1:
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    return layer, back


def render_flow(flow: dict, pid=None, finding_sev=None) -> str:
    nodes, edges = flow["nodes"], flow["edges"]
    layer, back = _layers(nodes, edges)
    geo = {}
    for n in nodes:
        lines = wrap(n["text"], 15 if n["kind"] == "decision" else 24)
        h = max(40, len(lines) * LINE_H + 2 * 10)
        if n["kind"] == "decision":
            h += 22
        geo[n["id"]] = {"lines": lines, "h": h, "kind": n["kind"], "layer": layer[n["id"]]}
    rows = {}
    for n in nodes:
        rows.setdefault(geo[n["id"]]["layer"], []).append(n["id"])
    width_cells = max(len(r) for r in rows.values())
    width = width_cells * NODE_W + (width_cells - 1) * GAP_X + 2 * PAD + 70  # room on the right for loop-back edges
    y = PAD
    for li in sorted(rows):
        row_h = max(geo[i]["h"] for i in rows[li])
        total = len(rows[li]) * NODE_W + (len(rows[li]) - 1) * GAP_X
        x = (width - 70 - total) / 2.0
        for i in rows[li]:
            g = geo[i]
            g["x"], g["y"], g["w"] = x, y + (row_h - g["h"]) / 2.0, NODE_W
            x += NODE_W + GAP_X
        y += row_h + GAP_Y
    height = y - GAP_Y + PAD
    parts = [
        '<svg class="flowsvg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
        % (width, height, width, height, esc(flow["title"] or "Flowchart")),
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>',
    ]
    for a, b, label in edges:
        ga, gb = geo[a], geo[b]
        if a == b:
            x1 = ga["x"] + ga["w"]
            yy = ga["y"] + ga["h"] / 2.0
            d = "M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" % (x1, yy - 8, x1 + 40, yy - 30, x1 + 40, yy + 30, x1, yy + 8)
            lx, ly = x1 + 44, yy
        elif (a, b) in back or gb["layer"] <= ga["layer"]:
            x1, y1 = ga["x"] + ga["w"], ga["y"] + ga["h"] / 2.0
            x2, y2 = gb["x"] + gb["w"], gb["y"] + gb["h"] / 2.0
            off = width - 22
            d = "M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" % (x1, y1, off, y1, off, y2, x2, y2)
            lx, ly = off - 4, (y1 + y2) / 2.0
        else:
            x1, y1 = ga["x"] + ga["w"] / 2.0, ga["y"] + ga["h"]
            x2, y2 = gb["x"] + gb["w"] / 2.0, gb["y"]
            mid = (y1 + y2) / 2.0
            d = "M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" % (x1, y1, x1, mid, x2, mid, x2, y2)
            lx, ly = (x1 + x2) / 2.0, mid - 4
        parts.append('<path class="edge" d="%s" fill="none" stroke="currentColor" stroke-width="1.6" marker-end="url(#ah)"/>' % d)
        if label:
            parts.append('<text class="elabel" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (lx, ly, esc(label)))
    for n in nodes:
        g = geo[n["id"]]
        cx, cy = g["x"] + g["w"] / 2.0, g["y"] + g["h"] / 2.0
        if g["kind"] == "decision":
            shape = '<polygon class="node k-decision" points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f"/>' % (
                cx, g["y"], g["x"] + g["w"], cy, cx, g["y"] + g["h"], g["x"], cy)
        else:
            rx = 20 if g["kind"] == "start" else 8
            shape = '<rect class="node k-%s" x="%.1f" y="%.1f" width="%d" height="%.1f" rx="%d"/>' % (
                g["kind"], g["x"], g["y"], g["w"], g["h"], rx)
        start = cy - (len(g["lines"]) - 1) * LINE_H / 2.0 + 5
        text = "".join(
            '<tspan x="%.1f" y="%.1f">%s</tspan>' % (cx, start + k * LINE_H, esc(l)) for k, l in enumerate(g["lines"])
        )
        badges = []
        for k, num in enumerate(reversed(n["pins"])):
            sev = (finding_sev or {}).get(num, "")
            bx = g["x"] + g["w"] - 8 - (k + 1) * 50 + 4
            by = g["y"] - 9
            badges.append(
                '<a href="#f-%s-%s"><g class="pin %s"><rect x="%.1f" y="%.1f" width="46" height="18" rx="9"/>'
                '<text x="%.1f" y="%.1f" text-anchor="middle">%s #%s</text></g></a>'
                % (esc(pid), num, esc(sev.lower() or "px"), bx, by, bx + 23, by + 13, esc(sev), num)
            )
        parts.append('<g>%s<text class="ntext" text-anchor="middle">%s</text>%s</g>' % (shape, text, "".join(badges)))
    parts.append("</svg>")
    cap = '<div class="flow-title">%s</div>' % esc(flow["title"]) if flow["title"] else ""
    tools = '<button type="button" class="flow-png" title="Download this flowchart as an image">Save PNG</button>'
    return '<figure class="flow">%s%s<div class="flow-scroll">%s</div></figure>' % (cap, tools, "".join(parts))


def severity_chart(prs: list) -> str:
    """One stacked bar per run: how many findings at each severity."""
    c = {s: 0 for s in SEVERITIES}
    for pr in prs:
        for s, k in counts(pr["findings"]).items():
            c[s] += k
    total = sum(c.values())
    if not total:
        return ""
    segs = "".join(
        '<span class="seg sev %s" style="flex:%d" title="%s: %d">%s &middot; %d</span>' % (s.lower(), c[s], s, c[s], s, c[s])
        for s in SEVERITIES if c[s]
    )
    return '<div class="chart"><div class="chart-title">Findings by severity</div><div class="stack">%s</div></div>' % segs


def file_chart(prs: list) -> str:
    """Horizontal bars: findings per file, most first, with the highest severity as the color."""
    per = {}
    for pr in prs:
        for f in pr["findings"]:
            name = str(f.get("filePath", "")).rsplit("/", 1)[-1] or "?"
            sev = str(f.get("severity", "")).upper()
            ent = per.setdefault(name, {"n": 0, "sev": "P5"})
            ent["n"] += 1
            if sev in SEVERITIES and SEVERITIES.index(sev) < SEVERITIES.index(ent["sev"]):
                ent["sev"] = sev
    if not per:
        return ""
    top = sorted(per.items(), key=lambda kv: (-kv[1]["n"], kv[0]))[:8]
    peak = max(v["n"] for _k, v in top)
    rows = "".join(
        '<div class="hrow"><span class="hname"><code>%s</code></span><span class="hbar"><span class="fill sev %s" '
        'style="width:%d%%"></span></span><span class="hnum">%d</span></div>'
        % (esc(k), v["sev"].lower(), max(6, 100 * v["n"] // peak), v["n"])
        for k, v in top
    )
    return '<div class="chart"><div class="chart-title">Where the findings are</div>%s</div>' % rows


def brand_header(version: str) -> str:
    return (
        '<div class="brand">%s<div class="brand-text"><span class="brand-name">AdversaryPR</span>'
        '<span class="brand-ver">v%s</span></div>'
        '<a class="brand-link" href="https://adversarypr.com" target="_blank" rel="noopener noreferrer">adversarypr.com</a></div>'
        % (logo_svg(40), esc(version))
    )


def brand_footer(version: str) -> str:
    return (
        '<footer class="brand-foot">%s<span>Reviewed with <strong>AdversaryPR</strong> v%s &middot; '
        '<a href="https://adversarypr.com" target="_blank" rel="noopener noreferrer">adversarypr.com</a></span></footer>'
        % (logo_svg(20), esc(version))
    )


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
                "overview": (found or {}).get("overview"),
                "impact": (found or {}).get("impact"),
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
    flow = check_flow(f.get("flow"), ref, problems)
    flow_html = render_flow(flow) if flow else ""
    return (
        '<article class="finding" id="f-{pid}-{n}">'
        '<header><label class="pick-wrap"><input type="checkbox" class="pick" data-n="{n}" checked> '
        '<span class="ref">{ref}</span></label>'
        '<span class="sev {sevc}">{sev}</span><span class="summary">{summary}</span></header>'
        '<p class="where"><code>{path}</code> {where} &middot; {rule}</p>'
        "{warn}{code}{flow}"
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
        flow=flow_html,
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


IMPACT_LABELS = {1: "Contained", 2: "Local", 3: "Shared", 4: "Wide", 5: "Foundational"}
FIT_STATUSES = ("current", "behind", "overlaps", "conflicts", "unknown")
GLYPH = {"start": "\u25b6", "step": "\u2022", "decision": "\u25c7", "bad": "\u2717", "ok": "\u2713", "note": "i"}


def _plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def fit_text(meta: dict):
    """One line saying whether the PR still fits its target branch, or None when it was not checked."""
    fr = meta.get("freshness")
    if not isinstance(fr, dict) or fr.get("status") not in FIT_STATUSES:
        return None
    target = meta.get("targetBranch") or "the target branch"
    behind = fr.get("behindBy")
    behind_txt = "%s behind %s" % (_plural(behind, "commit"), target) if isinstance(behind, int) and behind > 0 else ""
    files = lambda key: ", ".join(str(x) for x in (fr.get(key) or [])[:5])
    st = fr["status"]
    if st == "current":
        return "Up to date with %s" % target
    if st == "behind":
        if fr.get("overlapChecked") is False:
            return "%s; whether its files changed there was not fully checked%s" % (
                behind_txt or "Behind " + target, " (%s)" % fr["note"] if fr.get("note") else "")
        return "%s; none of its files changed there" % (behind_txt or "Behind " + target)
    if st == "overlaps":
        return "%s; also changed on %s: %s" % (behind_txt or "Behind " + target, target, files("overlapFiles") or "see pr.json")
    if st == "conflicts":
        return "Does not merge cleanly into %s: %s" % (target, files("conflictFiles") or "conflicts")
    return "Could not tell if it still fits %s%s" % (target, " (%s)" % fr["note"] if fr.get("note") else "")


def check_impact(impact, where: str, problems: list, required: bool):
    """Return a cleaned impact dict {score, label, reasons}, or None (with a WARNING when required or malformed)."""
    if impact in (None, "", {}):
        if required:
            problems.append("%s: no impact score; add impact {score 1-5, reasons} to findings.json" % where)
        return None
    try:
        score = int(impact.get("score")) if isinstance(impact, dict) else None
    except (TypeError, ValueError):
        score = None
    if score not in IMPACT_LABELS:
        problems.append("%s: impact.score must be a whole number from 1 to 5" % where)
        return None
    reasons = [str(r) for r in (impact.get("reasons") or []) if str(r).strip()][:4]
    if not reasons:
        problems.append("%s: impact needs at least one reason" % where)
    return {"score": score, "label": IMPACT_LABELS[score], "reasons": reasons, "basis": str(impact.get("basis") or "")}


def impact_text(impact: dict) -> str:
    basis = " (%s)" % impact["basis"] if impact.get("basis") else ""
    return "Impact %d/5, %s%s: %s" % (impact["score"], impact["label"], basis, "; ".join(impact["reasons"]) or "no reason given")


def flow_text(flow: dict, sev_of: dict) -> list:
    """The overview as numbered plain-text steps, for the chat."""
    nodes, edges = flow["nodes"], flow["edges"]
    layer, back = _layers(nodes, edges)
    order = sorted(range(len(nodes)), key=lambda i: (layer[nodes[i]["id"]], i))
    num = {nodes[i]["id"]: k + 1 for k, i in enumerate(order)}
    lines = []
    for i in order:
        nd = nodes[i]
        pins = " ".join("[%s #%d]" % (sev_of.get(n_, "?"), n_) for n_ in nd["pins"])
        lines.append("%2d. %s %s%s" % (num[nd["id"]], GLYPH.get(nd["kind"], "\u2022"), nd["text"], "  " + pins if pins else ""))
        outs = [e for e in edges if e[0] == nd["id"]]
        for k, (a, b, label) in enumerate(outs):
            bar = "\u2514" if k == len(outs) - 1 else "\u251c"
            loop = " (loops back)" if (a, b) in back or a == b else ""
            lines.append("      %s %s\u2192 %d%s" % (bar, label + " " if label else "", num[b], loop))
    return lines


def print_text(prs: list, problems: list) -> None:
    for pr in prs:
        meta = pr["meta"]
        print("%s \u00b7 %s" % (pr_label(meta, pr["id"]), meta.get("title") or "(no title)"))
        if pr["status"] != "ok":
            print("  %s" % pr["status"])
            continue
        fit = fit_text(meta)
        print("  Fit: %s" % (fit or "not checked"))
        impact = check_impact(pr.get("impact"), "PR %s" % pr["id"], problems, True)
        if impact:
            print("  %s" % impact_text(impact))
        sev_of = {}
        for f_ in pr["findings"]:
            try:
                sev_of[int(f_.get("n"))] = str(f_.get("severity", "")).upper()
            except (TypeError, ValueError):
                pass
        overview = check_flow(pr.get("overview"), "PR %s overview" % pr["id"], problems, sev_of)
        if overview:
            print("  How the change works%s" % (": " + overview["title"] if overview["title"] else ""))
            for line in flow_text(overview, sev_of):
                print("  " + line)
        else:
            problems.append("PR %s: no overview flowchart; add one showing how the changed code works" % pr["id"])
        print()


def render_scorecard(pr: dict, problems: list) -> str:
    """Impact (a five-segment meter) and fit, side by side, under the PR heading."""
    meta = pr["meta"]
    cards = []
    impact = check_impact(pr.get("impact"), "PR %s" % pr["id"], problems, True)
    if impact:
        segs = "".join('<i class="%s"></i>' % ("on" if k < impact["score"] else "") for k in range(5))
        basis = '<span class="basis">%s</span>' % esc(impact["basis"]) if impact["basis"] else ""
        cards.append(
            '<div class="sc-card"><div class="sc-k">Impact on the codebase</div>'
            '<div class="sc-v"><b>%d</b><span class="of"> / 5</span> %s</div>'
            '<div class="meter" role="img" aria-label="Impact %d of 5">%s</div>'
            '<div class="sc-why">%s %s</div></div>'
            % (impact["score"], esc(impact["label"]), impact["score"], segs, esc("; ".join(impact["reasons"])), basis)
        )
    fit = fit_text(meta)
    if fit:
        status = (meta.get("freshness") or {}).get("status")
        word = {"current": "Up to date", "behind": "Behind", "overlaps": "Overlaps", "conflicts": "Conflicts"}.get(status, "Unclear")
        bad = " bad" if status in ("conflicts", "overlaps") else ""
        cards.append(
            '<div class="sc-card%s"><div class="sc-k">Fit with %s</div><div class="sc-v"><b>%s</b></div>'
            '<div class="sc-why">%s</div></div>' % (bad, esc(meta.get("targetBranch") or "the target branch"), word, esc(fit))
        )
    return '<div class="scorecard">%s</div>' % "".join(cards) if cards else ""


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
    else:
        parts.append(render_scorecard(pr, problems))
    sev_of = {}
    for f_ in pr["findings"]:
        try:
            sev_of[int(f_.get("n"))] = str(f_.get("severity", "")).upper()
        except (TypeError, ValueError):
            pass
    overview = check_flow(pr.get("overview"), "PR %s overview" % pr["id"], problems, sev_of)
    if overview:
        parts.append('<div class="chart-title">How the change works</div>' + render_flow(overview, pr["id"], sev_of))
        if any(nd["pins"] for nd in overview["nodes"]):
            parts.append('<p class="meta">Badges mark the steps where a finding sits. Click one to jump to it.</p>')
    elif pr["status"] == "ok" and not pr.get("overview"):
        problems.append("PR %s: no overview flowchart; add one showing how the changed code works" % pr["id"])
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
.scorecard{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}
.sc-card{flex:1 1 280px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.sc-card.bad{border-color:var(--warn-fg)}
.sc-k{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.sc-v{font-size:20px;margin:2px 0 6px}.sc-v b{font-size:26px}.sc-v .of{color:var(--muted);font-size:14px}
.meter{display:flex;gap:4px;margin:4px 0 8px}.meter i{flex:1;height:8px;border-radius:4px;background:var(--line)}.meter i.on{background:var(--fg)}
.sc-why{color:var(--muted);font-size:14px}.sc-why .basis{font-style:italic}
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
.bar .btn{padding:8px 12px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);text-decoration:none;font:inherit}
.bar button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.bar .count{color:var(--muted);font-size:13px}

.brand{display:flex;align-items:center;gap:12px;padding:6px 0 14px;border-bottom:1px solid var(--line);margin-bottom:14px;color:var(--fg)}
.logo{flex:none;color:var(--fg)}
.brand-text{display:flex;flex-direction:column;line-height:1.15}
.brand-name{font-size:20px;font-weight:800;letter-spacing:.01em}
.brand-ver{font-size:12px;color:var(--muted)}
.brand-link{margin-left:auto;font-size:13px}
.brand-foot{display:flex;align-items:center;gap:8px;justify-content:center;margin-top:36px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
.brand-foot .logo{color:var(--muted)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:12px 0 8px}
.chart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.chart-title{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin:0 0 8px}
.stack{display:flex;gap:2px;border-radius:6px;overflow:hidden}
.stack .seg{flex-basis:0;min-width:42px;padding:6px 4px;border-radius:0;font-size:12.5px;text-align:center;white-space:nowrap}
.hrow{display:grid;grid-template-columns:minmax(80px,38%) 1fr 26px;gap:8px;align-items:center;margin:5px 0;font-size:13px}
.hname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hbar{background:var(--code);border-radius:4px;height:12px;overflow:hidden}
.fill{display:block;height:100%;border-radius:4px;min-width:0;padding:0}
.hnum{color:var(--muted);text-align:right}
figure.flow{margin:12px 0;padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:10px;color:var(--muted)}
.flow-title{font-size:12px;text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.flow-scroll{overflow-x:auto;text-align:center}
.flowsvg{max-width:100%;height:auto;color:var(--muted);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.flowsvg .node{fill:var(--code);stroke:var(--line);stroke-width:1.4}
.flowsvg .k-start{fill:var(--accent);stroke:var(--accent)}
.flowsvg .k-decision{fill:var(--warn-bg);stroke:var(--target-edge)}
.flowsvg .k-bad{fill:var(--del);stroke:var(--del-mk)}
.flowsvg .k-ok{fill:var(--add);stroke:var(--add-mk)}
.flowsvg .k-note{fill:var(--card);stroke:var(--line);stroke-dasharray:4 3}
.flowsvg .ntext{fill:var(--fg);font-size:12.5px}
.flowsvg .k-start+.ntext{fill:#fff}
.flowsvg .elabel{fill:var(--muted);font-size:11.5px;paint-order:stroke;stroke:var(--card);stroke-width:4px}
.charts{align-items:start}
figure.flow{width:fit-content;max-width:100%;min-width:min(100%,380px);position:relative}
.flow-png{position:absolute;top:8px;right:10px;padding:3px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--muted);font-size:12px;font-family:inherit;cursor:pointer}
.flowsvg .pin rect{stroke:var(--card);stroke-width:2}
.flowsvg .pin text{fill:#fff;font-size:10.5px;font-weight:700}
.flowsvg .pin.p1 rect{fill:var(--p1)}.flowsvg .pin.p2 rect{fill:var(--p2)}.flowsvg .pin.p3 rect{fill:var(--p3)}
.flowsvg .pin.p4 rect{fill:var(--p4)}.flowsvg .pin.p5 rect,.flowsvg .pin.px rect{fill:var(--p5)}
.exporting .bar,.exporting .flow-png{display:none}
@media print{
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
.bar,.flow-png,.pick{display:none}
main{padding-bottom:24px;max-width:none}
.finding,figure.flow,.chart{break-inside:avoid}
details.raw{display:none}
}
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
  document.documentElement.setAttribute('data-h',document.documentElement.scrollHeight);
  if(location.hash==='#export')document.documentElement.classList.add('exporting');
  var pdf=document.getElementById('pdf');
  if(pdf&&pdf.tagName==='BUTTON')pdf.onclick=function(){window.print()};
  function toPng(svg,done){
    var clone=svg.cloneNode(true),a=svg.querySelectorAll('*'),b=clone.querySelectorAll('*'),
      keys=['fill','stroke','stroke-width','stroke-dasharray','font-size','font-weight','font-family'];
    for(var i=0;i<a.length;i++){var cs=getComputedStyle(a[i]);
      keys.forEach(function(k){b[i].style.setProperty(k,cs.getPropertyValue(k))});}
    clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
    var w=+svg.getAttribute('width'),h=+svg.getAttribute('height');
    var img=new Image();
    img.onload=function(){var c=document.createElement('canvas');c.width=w*2;c.height=h*2;
      var x=c.getContext('2d');x.fillStyle=getComputedStyle(document.body).backgroundColor;x.fillRect(0,0,c.width,c.height);
      x.drawImage(img,0,0,c.width,c.height);done(c.toDataURL('image/png'));};
    img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(clone));
  }
  window.__adversary={png:toPng};
  [].slice.call(document.querySelectorAll('.flow-png')).forEach(function(btn,i){
    btn.onclick=function(){toPng(btn.parentNode.querySelector('svg'),function(url){
      var l=document.createElement('a');l.href=url;l.download='adversarypr-flowchart-'+(i+1)+'.png';
      document.body.appendChild(l);l.click();l.remove();});};
  });
})();
"""


def pdf_control(href) -> str:
    if href:
        return '<a id="pdf" class="btn" href="%s" download="adversarypr-review.pdf">Download PDF</a>' % esc(href)
    return '<button id="pdf" title="Opens the print dialog; choose Save as PDF">Save as PDF</button>'


def render_page(prs: list, version: str, run_dir: Path, problems: list, pdf_href=None) -> str:
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
                '<tr><td><a href="#pr-{id}">{id}</a></td><td>{title}</td><td>{imp}</td><td>{fit}</td>{cells}<td>{status}</td></tr>'.format(
                    id=esc(pr["id"]), title=esc(pr["meta"].get("title", "")), cells=cells, status=esc(pr["status"]),
                    imp=esc("%s of 5" % pr["impact"]["score"]) if isinstance(pr.get("impact"), dict) and pr["status"] == "ok" else "&mdash;",
                    fit=esc(((pr["meta"].get("freshness") or {}).get("status") or "not checked")) if pr["status"] == "ok" else "&mdash;",
                )
            )
        body.append(
            '<table class="summary"><thead><tr><th>PR</th><th>Title</th><th>Impact</th><th>Fit</th>%s<th>Status</th></tr></thead>'
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
<title>AdversaryPR v{version} preview</title>
<style>{css}</style></head>
<body><main>
{brand}
<h1>{heading}</h1>
{charts}
<p class="lede">Generated {when}. Nothing is posted from this page. Untick what you don't want, then copy the reply at the bottom into Claude. {hint}</p>
<p class="meta">Run folder: <code>{run_dir}</code></p>
{body}
{brand_foot}
</main>
<div class="bar"><div class="bar-inner">
<span class="count" id="count"></span>
<input type="text" id="reply" readonly aria-label="Reply to type into Claude">
<button id="copy" class="primary">Copy reply</button>
<button id="all">Select all</button><button id="none">Select none</button>
{pdf_control}
</div></div>
<script>{js}</script>
</body></html>
""".format(
        css=CSS,
        version=esc(version),
        pdf_control=pdf_control(pdf_href),
        brand=brand_header(version),
        brand_foot=brand_footer(version),
        charts='<div class="charts">%s%s</div>' % (severity_chart(prs), file_chart(prs))
        if total
        else "",
        heading=esc(heading),
        when=esc(datetime.now().strftime("%Y-%m-%d %H:%M")),
        hint=hint,
        run_dir=esc(run_dir),
        body="\n".join(body),
        js=JS,
    )



# ------------------------------------------------------------------ export --

BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser():
    """A Chromium-based browser that is already installed, or None."""
    for cand in BROWSERS:
        if os.path.isabs(cand):
            if os.path.exists(cand):
                return cand
        elif shutil.which(cand):
            return shutil.which(cand)
    return None


def _headless(browser, extra, url, timeout=90):
    with tempfile.TemporaryDirectory(prefix="adversary-export-") as prof:
        cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
               "--user-data-dir=" + prof] + extra + [url]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def export_page(page: Path, kind: str, target: Path):
    """Save the page as a PDF or one tall PNG. Returns an error string, or None on success."""
    browser = find_browser()
    if not browser:
        return "no Chrome, Edge, Brave or Chromium found; open the page and use Save as PDF"
    url = page.resolve().as_uri() + "#export"
    try:
        if kind == "pdf":
            _headless(browser, ["--no-pdf-header-footer", "--print-to-pdf=" + str(target)], url)
        else:
            dom = _headless(browser, ["--dump-dom", "--virtual-time-budget=3000"], url).stdout
            m = re.search(r'data-h="(\d+)"', dom)
            height = min(max(int(m.group(1)) if m else 3000, 600), 16000)
            _headless(browser, ["--window-size=1100,%d" % (height + 20), "--screenshot=" + str(target)], url)
    except (OSError, subprocess.SubprocessError) as exc:
        return "export failed (%s)" % exc
    return None if target.exists() and target.stat().st_size > 0 else "the browser did not write %s" % target.name


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a AdversaryPR run folder as an HTML preview.")
    ap.add_argument("run_dir", help="the run's RUN_DIR")
    ap.add_argument("pr_ids", nargs="*", help="PR numbers, in the order to show them (default: all, ascending)")
    ap.add_argument("--version", default="?", help="AdversaryPR version, for the page heading")
    ap.add_argument("--pdf", nargs="?", const="", metavar="PATH", help="save the PDF here (default RUN_DIR/preview.pdf)")
    ap.add_argument("--no-pdf", action="store_true", help="do not save a PDF next to the page")
    ap.add_argument("--png", nargs="?", const="", metavar="PATH", help="also save the page as one tall PNG (default RUN_DIR/preview.png)")
    ap.add_argument("--text", action="store_true", help="print each PR's fit, impact and overview flowchart as plain text, and write nothing")
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
    if args.text:
        print_text(prs, problems)
        for p in problems:
            print("WARNING " + p)
        return 0
    out = run_dir / "preview.html"
    pdf_target = Path(args.pdf).expanduser().resolve() if args.pdf else run_dir / "preview.pdf"
    want_pdf = not args.no_pdf and find_browser() is not None
    href = pdf_target.name if want_pdf and pdf_target.parent == run_dir else (pdf_target.as_uri() if want_pdf else None)
    out.write_text(render_page(prs, args.version, run_dir, problems, href), encoding="utf-8")
    pdf_note = None
    if want_pdf:
        err = export_page(out, "pdf", pdf_target)
        if err:
            pdf_note = "WARNING PDF export: %s" % err
            out.write_text(render_page(prs, args.version, run_dir, problems, None), encoding="utf-8")
        else:
            pdf_note = "PDF: %s" % pdf_target

    print(out)
    print(out.resolve().as_uri())
    if pdf_note:
        print(pdf_note)
    if args.png is not None:
        target = Path(args.png).expanduser().resolve() if args.png else run_dir / "preview.png"
        err = export_page(out, "png", target)
        print("PNG: %s" % target if err is None else "WARNING PNG export: %s" % err)
    print("%d PR(s), %d finding(s)" % (len(prs), sum(len(p["findings"]) for p in prs)))
    for pr in prs:
        if pr["status"] != "ok":
            print("PR %s: %s" % (pr["id"], pr["status"]))
    for p in problems:
        print("WARNING " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

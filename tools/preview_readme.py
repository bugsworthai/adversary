#!/usr/bin/env python3
"""Render README.md as a local preview that looks like a GitHub repository page.

Usage:  python3 tools/preview_readme.py [--readme README.md] [--out preview/readme.html]

Writes ONE self-contained HTML file (inline CSS, no scripts, no external
requests). Relative image and link paths in the README are rewritten to
"../<path>" because the output lives in preview/. Standard library only,
Python 3.8+. Never touches the network.
"""
import argparse
import html
import os
import re
import sys

BANNED = re.compile(r"\b(hostile|hostility|switch)\b", re.I)

ALLOWED_TAGS = {
    "p", "picture", "source", "img", "br", "a", "details", "summary", "h1", "h2",
    "h3", "h4", "h5", "h6", "strong", "em", "b", "i", "code", "sub", "sup", "kbd",
    "div", "span", "hr", "table", "thead", "tbody", "tr", "th", "td", "ul", "ol",
    "li", "pre", "blockquote",
}
ALLOWED_ATTRS = {
    "align", "alt", "src", "srcset", "href", "media", "width", "height", "title",
    "name", "open", "id", "type", "colspan", "rowspan", "sizes",
}
VOID_TAGS = {"source", "img", "br", "hr"}
BLOCK_HTML_START = re.compile(
    r"^\s{0,3}<(p|picture|div|details|h[1-6]|table|summary|hr)\b", re.I)

URL_ATTR = re.compile(r'\b(src|href|srcset)="([^"]*)"')


# ---------------------------------------------------------------- sanitizing

def _is_unsafe_url(value):
    cleaned = re.sub(r"[\x00-\x20]+", "", html.unescape(value)).lower()
    return cleaned.startswith(("javascript:", "vbscript:", "data:text/html"))


def _sanitize_tag(match):
    closing, name, attrs, selfclose = match.group(1), match.group(2), match.group(3), match.group(4)
    lname = name.lower()
    if lname not in ALLOWED_TAGS:
        return html.escape(match.group(0))
    if closing:
        return "</%s>" % lname
    out = []
    for am in re.finditer(r"([A-Za-z_:][-\w:.]*)(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s\"'>]+))?", attrs):
        key = am.group(1).lower()
        val = am.group(2)
        if val is None:
            val = ""
        elif val[:1] in "\"'":
            val = val[1:-1]
        if key.startswith("on") or key not in ALLOWED_ATTRS:
            continue
        if key in ("src", "href", "srcset") and _is_unsafe_url(val):
            continue
        out.append(' %s="%s"' % (key, html.escape(html.unescape(val), quote=True)))
    return "<%s%s%s>" % (lname, "".join(out), " /" if (selfclose and lname in VOID_TAGS) else "")


TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*?)(/?)>")


def strip_dangerous(text):
    """Drop <script>/<style> blocks (with contents) and HTML comments."""
    text = re.sub(r"<script\b.*?</script\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r"<script\b[^>]*>", "", text, flags=re.I)
    text = re.sub(r"<style\b.*?</style\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return text


def sanitize_html(fragment):
    """Allow a small set of tags; escape everything else."""
    fragment = strip_dangerous(fragment)
    out, pos = [], 0
    for m in TAG_RE.finditer(fragment):
        out.append(_escape_text(fragment[pos:m.start()]))
        out.append(_sanitize_tag(m))
        pos = m.end()
    out.append(_escape_text(fragment[pos:]))
    return "".join(out)


def _escape_text(text):
    return _escape_keep_entities(text)


def _escape_keep_entities(text):
    text = re.sub(r"&(?!(#\d+|#x[0-9a-fA-F]+|\w+);)", "&amp;", text)
    return text.replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------- inline

def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.strip().replace(" ", "-")


def render_inline(text):
    stash = []

    def keep(s):
        stash.append(s)
        return "\x00%d\x00" % (len(stash) - 1)

    # code spans first, so nothing inside them is interpreted
    def code_span(m):
        return keep("<code>%s</code>" % html.escape(m.group(2).strip("\n"), quote=False))
    text = re.sub(r"(`+)(.+?)\1(?!`)", code_span, text)

    text = strip_dangerous(text)
    text = TAG_RE.sub(lambda m: keep(_sanitize_tag(m)), text)
    text = html.escape(text, quote=False)

    # images then links
    def image(m):
        alt, src = m.group(1), m.group(2)
        if _is_unsafe_url(src):
            return html.escape(alt)
        return keep('<img src="%s" alt="%s">' % (html.escape(src, quote=True), html.escape(alt, quote=True)))
    text = re.sub(r'!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+(?:&quot;|")[^)]*?(?:&quot;|"))?\s*\)', image, text)

    def link(m):
        label, href = m.group(1), m.group(2)
        if _is_unsafe_url(href):
            return label
        return '<a href="%s">%s</a>' % (html.escape(html.unescape(href), quote=True), label)
    text = re.sub(r'\[([^\]]+)\]\(\s*([^)\s]+)(?:\s+(?:&quot;|")[^)]*?(?:&quot;|"))?\s*\)', link, text)

    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])", r"<em>\1</em>", text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<del>\1</del>", text)

    prev = None
    while prev != text:  # restore placeholders (may nest inside link text)
        prev = text
        text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text


# -------------------------------------------------------------------- blocks

FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})\s*([\w+#.-]*)[^`]*$")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
HR_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
ULI_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
OLI_RE = re.compile(r"^(\s*)(\d{1,9})[.)]\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


class Stats:
    def __init__(self):
        self.headings = 0
        self.tables = 0
        self.anchors = set()


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells, cur, in_code = [], [], 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "`":
            in_code ^= 1
        if ch == "|" and not in_code:
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def _is_table_start(lines, i):
    return "|" in lines[i] and i + 1 < len(lines) and "|" in lines[i + 1] \
        and TABLE_SEP_RE.match(lines[i + 1]) and "-" in lines[i + 1]


def _starts_block(lines, i):
    line = lines[i]
    return bool(FENCE_RE.match(line) or HEADING_RE.match(line) or HR_RE.match(line)
                or line.lstrip().startswith(">") or ULI_RE.match(line) or OLI_RE.match(line)
                or BLOCK_HTML_START.match(line) or _is_table_start(lines, i))


def render_blocks(lines, stats):
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fm = FENCE_RE.match(line)
        if fm:
            fence, lang = fm.group(2), fm.group(3)
            indent = len(fm.group(1))
            body = []
            i += 1
            while i < n and not re.match(r"^\s{0,3}%s{%d,}\s*$" % (re.escape(fence[0]), len(fence)), lines[i]):
                body.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i])
                i += 1
            i += 1
            out.append(render_code(body, lang))
            continue

        hm = HEADING_RE.match(line)
        if hm:
            level, text = len(hm.group(1)), hm.group(2)
            stats.headings += 1
            slug = slugify(render_inline(text))
            stats.anchors.add(slug)
            out.append('<h%d id="%s">%s</h%d>' % (level, html.escape(slug), render_inline(text), level))
            i += 1
            continue

        if HR_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        if BLOCK_HTML_START.match(line):
            block = []
            while i < n and lines[i].strip():
                block.append(lines[i])
                i += 1
            raw = "\n".join(block)
            for hm2 in re.finditer(r'\bid="([^"]+)"', raw):
                stats.anchors.add(hm2.group(1))
            out.append(sanitize_html(raw))
            continue

        if line.lstrip().startswith(">"):
            block = []
            while i < n and lines[i].lstrip().startswith(">"):
                block.append(re.sub(r"^\s{0,3}>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>\n%s\n</blockquote>" % render_blocks(block, stats))
            continue

        if _is_table_start(lines, i):
            header = split_row(lines[i])
            seps = split_row(lines[i + 1])
            aligns = []
            for s in seps:
                s = s.strip()
                aligns.append("center" if s.startswith(":") and s.endswith(":") else
                              "right" if s.endswith(":") else "left" if s.startswith(":") else "")
            i += 2
            rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(split_row(lines[i]))
                i += 1
            stats.tables += 1
            out.append(render_table(header, aligns, rows))
            continue

        if ULI_RE.match(line) or OLI_RE.match(line):
            html_list, i = render_list(lines, i, stats)
            out.append(html_list)
            continue

        para = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not _starts_block(lines, i):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % render_inline("\n".join(para)))
    return "\n".join(out)


def render_table(header, aligns, rows):
    def cell(tag, text, k):
        a = aligns[k] if k < len(aligns) else ""
        style = ' align="%s"' % a if a else ""
        return "<%s%s>%s</%s>" % (tag, style, render_inline(text), tag)
    parts = ["<table>", "<thead><tr>%s</tr></thead>" % "".join(cell("th", h, k) for k, h in enumerate(header)), "<tbody>"]
    for r in rows:
        r = (r + [""] * len(header))[:len(header)]
        parts.append("<tr>%s</tr>" % "".join(cell("td", c, k) for k, c in enumerate(r)))
    parts.append("</tbody></table>")
    return "\n".join(parts)


def render_code(body, lang):
    label = '<span class="lang">%s</span>' % html.escape(lang) if lang else ""
    rendered = []
    for ln in body:
        esc = html.escape(ln, quote=False)
        if lang.lower() == "diff":
            if ln.startswith("+") and not ln.startswith("+++"):
                esc = '<span class="add">%s</span>' % esc
            elif ln.startswith("-") and not ln.startswith("---"):
                esc = '<span class="del">%s</span>' % esc
            elif ln.startswith("@@"):
                esc = '<span class="hunk">%s</span>' % esc
        rendered.append(esc)
    cls = ' class="lang-%s"' % html.escape(lang) if lang else ""
    return '<div class="codebox">%s<pre><code%s>%s</code></pre></div>' % (label, cls, "\n".join(rendered))


def render_list(lines, i, stats):
    first = ULI_RE.match(lines[i]) or OLI_RE.match(lines[i])
    base = len(first.group(1))
    ordered = bool(OLI_RE.match(lines[i]) and not ULI_RE.match(lines[i]))
    items = []
    n = len(lines)
    while i < n:
        m = (OLI_RE if ordered else ULI_RE).match(lines[i])
        if not m or len(m.group(1)) != base:
            break
        content_indent = len(lines[i]) - len(m.group(3))
        item = [m.group(3)]
        i += 1
        while i < n:
            ln = lines[i]
            if not ln.strip():
                # a blank line continues the item only if the next line is indented
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and (len(lines[j]) - len(lines[j].lstrip())) >= content_indent:
                    item.extend([""] * (j - i))
                    i = j
                    continue
                break
            indent = len(ln) - len(ln.lstrip())
            if indent >= content_indent:
                item.append(ln[content_indent:])
            elif indent > base and not (ULI_RE.match(ln) or OLI_RE.match(ln)):
                item.append(ln.strip())  # lazy continuation
            else:
                break
            i += 1
        items.append(item)
        # skip single blank lines between items of the same list
        j = i
        while j < n and not lines[j].strip():
            j += 1
        if j < n and j > i:
            mm = (OLI_RE if ordered else ULI_RE).match(lines[j])
            if mm and len(mm.group(1)) == base:
                i = j
    tag = "ol" if ordered else "ul"
    parts = ["<%s>" % tag]
    for item in items:
        inner = render_blocks(item, stats)
        # tight list: unwrap a lone leading paragraph
        inner = re.sub(r"^<p>(.*?)</p>", r"\1", inner, count=1, flags=re.S)
        parts.append("<li>%s</li>" % inner)
    parts.append("</%s>" % tag)
    return "\n".join(parts), i


def render_markdown(md, stats=None):
    stats = stats or Stats()
    md = md.replace("\r\n", "\n").replace("\t", "    ")
    return render_blocks(md.split("\n"), stats)


# ------------------------------------------------------------ path rewriting

def _is_external(url):
    u = url.strip().lower()
    return u.startswith(("http://", "https://", "//", "#", "mailto:", "data:", "tel:"))


def rewrite_paths(body, root, prefix="../"):
    """Rewrite relative src/href/srcset to prefix+path. Returns (html, missing_paths)."""
    missing = []

    def fix(url):
        if not url.strip() or _is_external(url):
            return url
        path = re.split(r"[#?]", html.unescape(url), 1)[0]
        if path and not os.path.exists(os.path.join(root, path)):
            missing.append(path)
        return prefix + (url[2:] if url.startswith("./") else url)

    def attr(m):
        name, val = m.group(1), m.group(2)
        if name == "srcset":
            parts = []
            for piece in val.split(","):
                bits = piece.strip().split(None, 1)
                if bits:
                    bits[0] = fix(bits[0])
                    parts.append(" ".join(bits))
            return 'srcset="%s"' % ", ".join(parts)
        return '%s="%s"' % (name, fix(val))
    return URL_ATTR.sub(attr, body), missing


def count_stats(body):
    return {
        "images": len(re.findall(r"<img\b", body)),
        "links": len(re.findall(r"<a\b[^>]*\bhref=", body)),
    }


def check_anchors(body, anchors):
    bad = []
    for m in re.finditer(r'\bhref="#([^"]*)"', body):
        if m.group(1) and m.group(1) not in anchors:
            bad.append(m.group(1))
    return bad


# ---------------------------------------------------------------------- page

CSS = """
:root{color-scheme:light dark;--bg:#fff;--bg2:#f6f8fa;--fg:#1f2328;--muted:#59636e;--border:#d1d9e0;--border2:#d1d9e0b3;--link:#0969da;--add:#dafbe1;--addfg:#116329;--del:#ffebe9;--delfg:#82071e;--hunk:#ddf4ff;--hunkfg:#0550ae;--bar:#25292e;--pill:#59636e}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--bg2:#151b23;--fg:#f0f6fc;--muted:#9198a1;--border:#3d444d;--border2:#3d444db3;--link:#4493f8;--add:#12261e;--addfg:#7ee787;--del:#2d1214;--delfg:#ffa198;--hunk:#0c2d6b;--hunkfg:#79c0ff;--bar:#010409;--pill:#9198a1}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif}
.topbar{background:var(--bar);color:#f0f6fc;padding:14px 32px;display:flex;gap:16px;align-items:center;font-weight:600}
.topbar .dot{width:24px;height:24px;border-radius:50%;background:#f0f6fc;display:inline-block}
.topbar .note{margin-left:auto;font-weight:400;font-size:12px;opacity:.7}
.repo{max-width:1012px;margin:0 auto;padding:24px 16px 0}
.repo h1.name{font-size:20px;font-weight:400;margin:0 0 8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.repo .owner{color:var(--link)}
.pill{border:1px solid var(--border);color:var(--pill);border-radius:2em;padding:0 7px;font-size:12px;font-weight:500;line-height:18px}
.repo .desc{margin:0 0 16px;color:var(--muted)}
.filebox{max-width:1012px;margin:0 auto 40px;border:1px solid var(--border);border-radius:6px}
.filehead{background:var(--bg2);border-bottom:1px solid var(--border);border-radius:6px 6px 0 0;padding:10px 16px;font-size:14px;font-weight:600}
.markdown-body{padding:32px;font-size:16px;line-height:1.5;word-wrap:break-word;overflow-wrap:anywhere}
.markdown-body>*:first-child{margin-top:0!important}
.markdown-body h1,.markdown-body h2,.markdown-body h3,.markdown-body h4{margin:24px 0 16px;font-weight:600;line-height:1.25}
.markdown-body h1{font-size:2em;padding-bottom:.3em;border-bottom:1px solid var(--border2)}
.markdown-body h2{font-size:1.5em;padding-bottom:.3em;border-bottom:1px solid var(--border2)}
.markdown-body h3{font-size:1.25em}.markdown-body h4{font-size:1em}
.markdown-body p,.markdown-body ul,.markdown-body ol,.markdown-body table,.markdown-body blockquote,.markdown-body .codebox,.markdown-body details{margin:0 0 16px}
.markdown-body a{color:var(--link);text-decoration:none}.markdown-body a:hover{text-decoration:underline}
.markdown-body img{max-width:100%;vertical-align:middle;background:transparent}
.markdown-body ul,.markdown-body ol{padding-left:2em}
.markdown-body li+li{margin-top:.25em}.markdown-body li>ul,.markdown-body li>ol{margin:.25em 0 0}
.markdown-body hr{height:.25em;padding:0;margin:24px 0;background:var(--border);border:0}
.markdown-body blockquote{padding:0 1em;color:var(--muted);border-left:.25em solid var(--border)}
.markdown-body blockquote>*:last-child{margin-bottom:0}
.markdown-body code{padding:.2em .4em;margin:0;font-size:85%;background:#818b981f;border-radius:6px;font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
.markdown-body .codebox{position:relative;background:var(--bg2);border-radius:6px}
.markdown-body .codebox .lang{position:absolute;top:4px;right:10px;font-size:11px;color:var(--muted);font-family:ui-monospace,Menlo,monospace}
.markdown-body pre{margin:0;padding:16px;overflow:auto;font-size:85%;line-height:1.45}
.markdown-body pre code{padding:0;background:transparent;font-size:100%;white-space:pre}
.markdown-body pre .add,.markdown-body pre .del,.markdown-body pre .hunk{display:block;margin:0 -16px;padding:0 16px}
.markdown-body pre .add{background:var(--add);color:var(--addfg)}
.markdown-body pre .del{background:var(--del);color:var(--delfg)}
.markdown-body pre .hunk{background:var(--hunk);color:var(--hunkfg)}
.markdown-body table{border-spacing:0;border-collapse:collapse;display:block;width:max-content;max-width:100%;overflow:auto}
.markdown-body th,.markdown-body td{padding:6px 13px;border:1px solid var(--border);vertical-align:top}
.markdown-body th{font-weight:600}
.markdown-body tr{background:var(--bg);border-top:1px solid var(--border)}
.markdown-body tbody tr:nth-child(2n){background:var(--bg2)}
.markdown-body summary{cursor:pointer}
.markdown-body sub{font-size:75%}
.footer{max-width:1012px;margin:-24px auto 40px;padding:0 16px;color:var(--muted);font-size:12px}
"""


def build_page(md, title="adversarypr"):
    stats = Stats()
    body = render_markdown(md, stats)
    return body, stats


def page_html(body):
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>adversarypr: README preview</title>
<style>%s</style></head>
<body>
<div class="topbar"><span class="dot"></span><span>GitHub-style preview</span><span class="note">Local file. Generated by tools/preview_readme.py. Not GitHub.</span></div>
<div class="repo">
<h1 class="name"><span class="owner">your-org</span> / <strong>adversarypr</strong> <span class="pill">Public</span></h1>
<p class="desc">A careful review of Azure DevOps and GitHub pull requests, as a Claude skill. Free and open source.</p>
</div>
<div class="filebox"><div class="filehead">README.md</div>
<article class="markdown-body">
%s
</article></div>
<div class="footer">Preview only. Image and link paths resolve against the repo root (../). Colours follow your system light or dark setting.</div>
</body></html>
""" % (CSS, body)


def run(readme, out, root=None):
    """Render readme to out. Returns (stats_dict, warnings)."""
    root = root or os.path.dirname(os.path.abspath(readme))
    with open(readme, encoding="utf-8") as fh:
        md = fh.read()
    warnings = []
    for m in BANNED.finditer(md):
        line = md.count("\n", 0, m.start()) + 1
        warnings.append("README.md line %d contains the word '%s'" % (line, m.group(0)))
    body, stats = build_page(md)
    body, missing = rewrite_paths(body, root)
    for path in sorted(set(missing)):
        warnings.append("missing local file referenced: %s" % path)
    for anchor in sorted(set(check_anchors(body, stats.anchors))):
        warnings.append("anchor link #%s has no matching heading" % anchor)
    counts = count_stats(body)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page_html(body))
    info = {"headings": stats.headings, "images": counts["images"],
            "tables": stats.tables, "links": counts["links"], "lines": md.count("\n") + 1}
    return info, warnings


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser(description="Preview README.md as a GitHub-style page.")
    ap.add_argument("--readme", default=os.path.join(root, "README.md"))
    ap.add_argument("--out", default=os.path.join(root, "preview", "readme.html"))
    args = ap.parse_args(argv)
    if not os.path.exists(args.readme):
        print("README not found: %s" % args.readme, file=sys.stderr)
        return 2
    info, warnings = run(args.readme, args.out)
    print("Wrote %s" % os.path.abspath(args.out))
    print("Stats: %(lines)d lines, %(headings)d headings, %(images)d images, %(tables)d tables, %(links)d links" % info)
    for w in warnings:
        print("WARNING: %s" % w)
    print("%d warning(s)" % len(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())

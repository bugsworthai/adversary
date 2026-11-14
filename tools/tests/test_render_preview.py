"""Offline tests for the 2.11.0 preview renderer. Nothing here touches the network."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill-source" / "adversary" / "versions" / "2.11.0" / "scripts" / "render_preview.py"
spec = importlib.util.spec_from_file_location("render_preview", SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

DIFF = """diff --git a/src/orders/Invoice.kt b/src/orders/Invoice.kt
--- a/src/orders/Invoice.kt
+++ b/src/orders/Invoice.kt
@@ -10,6 +10,8 @@ class Invoice {
 fun a() {}
+fun b() {}
+fun c() {}
 fun d() {}
-fun old() {}
 fun e() {}
 fun f() {}
@@ -40,3 +42,4 @@ class Other {
 fun g() {}
+fun h() {}
 fun i() {}
 fun j() {}
"""

SUGGEST = "**T**\n\nI noticed x. Is there a reason?\n\nPlease take a look at the suggested fix below, unless this was intentional.\n\n```suggestion\nfun b() {}\nfun c() {}\n```\n"
PLAIN = "**T**\n\nWhy.\n\n```kotlin\nfun b() {}\n```\n"


def run(provider, findings, path_prefix=""):
    """Render a one-PR run folder and return (stdout, html)."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    pr = root / "PR-1"
    pr.mkdir()
    (pr / "diff.patch").write_text(DIFF, encoding="utf-8")
    (pr / "pr.json").write_text(json.dumps({"provider": provider, "prId": 1, "title": "t"}), encoding="utf-8")
    for f in findings:
        f.setdefault("filePath", path_prefix + "src/orders/Invoice.kt")
        f.setdefault("severity", "P2")
        f.setdefault("summary", "s")
        f.setdefault("ruleSet", "r")
    (pr / "findings.json").write_text(json.dumps({"prId": 1, "status": "ok", "findings": findings}), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(root), "1", "--version", "2.11.0"],
                          capture_output=True, text=True)
    page = (root / "preview.html").read_text(encoding="utf-8") if (root / "preview.html").exists() else ""
    tmp.cleanup()
    return proc.stdout + proc.stderr, page


def finding(n=1, line=12, content=PLAIN, **kw):
    d = {"n": n, "line": line, "content": content}
    d.update(kw)
    return d


class StartLine(unittest.TestCase):
    def test_range_ok_and_highlighted(self):
        out, page = run("github", [finding(startLine=11, line=12)])
        self.assertNotIn("WARNING", out)
        self.assertIn("lines 11-12", page)
        self.assertEqual(page.count("tr class=\"add target\""), 2)

    def test_range_across_hunks_warns(self):
        out, _ = run("github", [finding(startLine=12, line=43)])
        self.assertIn("WARNING", out)
        self.assertIn("one hunk", out)

    def test_range_over_removed_line_warns(self):
        # new lines 13 (context d) and 14 (context e) surround the removed line
        out, _ = run("github", [finding(startLine=13, line=14)])
        self.assertIn("WARNING", out)

    def test_start_after_line_warns(self):
        out, _ = run("github", [finding(startLine=12, line=11)])
        self.assertIn("WARNING", out)

    def test_equal_start_is_single_line(self):
        out, _ = run("github", [finding(startLine=12, line=12)])
        self.assertNotIn("WARNING", out)


class Suggestion(unittest.TestCase):
    def test_suggestion_on_ado_warns(self):
        out, _ = run("ado", [finding(content=SUGGEST, suggestion=True)], path_prefix="/")
        self.assertIn("WARNING", out)
        self.assertIn("Azure DevOps", out)

    def test_suggestion_on_github_ok(self):
        out, page = run("github", [finding(startLine=11, line=12, content=SUGGEST, suggestion=True)])
        self.assertNotIn("WARNING", out)
        self.assertIn("Suggested change", page)

    def test_suggestion_without_valid_anchor_warns(self):
        out, _ = run("github", [finding(line=999, content=SUGGEST, suggestion=True)])
        self.assertIn("valid anchor", out)

    def test_flag_mismatch_warns(self):
        out, _ = run("github", [finding(content=SUGGEST)])
        self.assertIn("suggestion", out)
        self.assertIn("WARNING", out)
        out, _ = run("github", [finding(content=PLAIN, suggestion=True)])
        self.assertIn("WARNING", out)

    def test_language_block_on_ado_ok(self):
        out, _ = run("ado", [finding(content=PLAIN)], path_prefix="/")
        self.assertNotIn("WARNING", out)


class Fences(unittest.TestCase):
    def render(self, text):
        return RP.render_markdown(text, [])

    def test_language_block(self):
        h = self.render("```kotlin\nval x = 1 < 2\n```")
        self.assertIn('<pre><code class="lang-kotlin">val x = 1 &lt; 2</code></pre>', h)

    def test_suggestion_block_labelled(self):
        h = self.render("```suggestion\nreturn a + b\n```")
        self.assertIn("Suggested change", h)
        self.assertIn("return a + b", h)

    def test_diff_block_colored(self):
        h = self.render("```diff\n-old\n+new\n same\n```")
        self.assertIn('dl del">-old', h)
        self.assertIn('dl add">+new', h)
        self.assertIn('dl ctx"> same', h)

    def test_html_in_block_escaped(self):
        self.assertNotIn("<script>", self.render("```suggestion\n<script>x</script>\n```"))


class ExistingWarnings(unittest.TestCase):
    def test_line_not_in_diff(self):
        out, _ = run("github", [finding(line=500)])
        self.assertIn("not an added or context line", out)

    def test_wrong_slash_github(self):
        out, _ = run("github", [finding(filePath="/src/orders/Invoice.kt")])
        self.assertIn("must not start with /", out)

    def test_wrong_slash_ado(self):
        out, _ = run("ado", [finding(filePath="src/orders/Invoice.kt")])
        self.assertIn("must start with /", out)

    def test_work_item_reference(self):
        out, _ = run("github", [finding(content="See #3 for this.\n")])
        self.assertIn("#3", out)
        self.assertIn("WARNING", out)


if __name__ == "__main__":
    unittest.main()


FOOTER = "Comment by sam using Adversary ([adversarypr.com](https://adversarypr.com))"
FOOTER_HTML = 'Comment by sam using Adversary (<a href="https://adversarypr.com" target="_blank" rel="noopener noreferrer">adversarypr.com</a>)'


class Links(unittest.TestCase):
    def test_link_renders_as_anchor(self):
        out = RP._inline("see [docs](https://example.com/a_b_c?x=1&y=2)", [])
        self.assertIn('<a href="https://example.com/a_b_c?x=1&amp;y=2"', out)
        self.assertIn(">docs</a>", out)
        self.assertNotIn("<em>", out)

    def test_javascript_url_not_linked(self):
        out = RP._inline("[x](javascript:alert(1))", [])
        self.assertNotIn("<a ", out)
        out = RP._inline("[x](JaVaScRiPt:alert(1)) [y](data:text/html,hi)", [])
        self.assertNotIn("<a ", out)

    def test_link_text_is_escaped(self):
        out = RP._inline("[<b>x</b>](https://example.com)", [])
        self.assertIn("&lt;b&gt;", out)
        self.assertNotIn("<b>", out)

    def test_footer_line_renders(self):
        out = RP._inline(FOOTER, [])
        self.assertEqual(out, FOOTER_HTML)

    def test_footer_in_page_and_raw_view(self):
        out, page = run("github", [finding(content=PLAIN + "\n" + FOOTER)])
        self.assertNotIn("WARNING", out)
        self.assertIn(FOOTER_HTML, page)
        # exact-text view keeps the raw markdown
        self.assertIn("<pre>" + PLAIN.replace("\n", "\n") .split("\n")[0], page)
        self.assertIn("Adversary ([adversarypr.com](https://adversarypr.com))", page)

    def test_footer_without_name(self):
        out = RP._inline("Comment using Adversary ([adversarypr.com](https://adversarypr.com))", [])
        self.assertIn('<a href="https://adversarypr.com"', out)

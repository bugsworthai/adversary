"""Offline tests for tools/preview_readme.py. No network."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("preview_readme", ROOT / "tools" / "preview_readme.py")
PR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PR)


def render(md):
    return PR.render_markdown(md)


class RenderTests(unittest.TestCase):
    def test_headings(self):
        out = render("# Title\n\n## Install and use\n\nText")
        self.assertIn('<h1 id="title">Title</h1>', out)
        self.assertIn('<h2 id="install-and-use">Install and use</h2>', out)
        self.assertIn("<p>Text</p>", out)

    def test_table_with_alignment(self):
        out = render("| A | B |\n|:--|--:|\n| 1 | `x|y` |\n")
        self.assertIn("<table>", out)
        self.assertIn('<th align="left">A</th>', out)
        self.assertIn('<th align="right">B</th>', out)
        self.assertIn("<code>x|y</code>", out)

    def test_diff_colouring_and_label(self):
        out = render("```diff\n-old\n+new\n same\n```")
        self.assertIn('<span class="del">-old</span>', out)
        self.assertIn('<span class="add">+new</span>', out)
        self.assertIn('<span class="lang">diff</span>', out)

    def test_lists_nested_and_ordered(self):
        out = render("- a\n  - b\n- c\n\n1. one\n2. two")
        self.assertEqual(out.count("<ul>"), 2)
        self.assertIn("<ol>", out)
        self.assertIn("<li>two</li>", out)

    def test_inline_and_escaping(self):
        out = render("**b** *i* `<x>` [l](https://e.com) <weird>")
        self.assertIn("<strong>b</strong>", out)
        self.assertIn("<em>i</em>", out)
        self.assertIn("<code>&lt;x&gt;</code>", out)
        self.assertIn('<a href="https://e.com">l</a>', out)
        self.assertIn("&lt;weird&gt;", out)

    def test_blockquote_and_hr(self):
        out = render("> quoted\n\n---")
        self.assertIn("<blockquote>", out)
        self.assertIn("<hr>", out)

    def test_picture_source_passthrough(self):
        md = ('<p align="center">\n<picture>\n'
              '<source media="(prefers-color-scheme: dark)" srcset="a-dark.svg">\n'
              '<img alt="x" src="a.svg">\n</picture>\n</p>')
        out = render(md)
        self.assertIn('<p align="center">', out)
        self.assertIn('<source media="(prefers-color-scheme: dark)" srcset="a-dark.svg">', out)
        self.assertIn('<img alt="x" src="a.svg">', out)

    def test_script_and_handlers_stripped(self):
        out = render('<p onclick="x()">hi <a href="javascript:alert(1)">l</a></p>\n\n'
                     '<script>alert(1)</script>\n\ntext <img src="a.png" onerror="x()">')
        self.assertNotIn("<script", out)
        self.assertNotIn("alert(1)", out)
        self.assertNotIn("onclick", out)
        self.assertNotIn("onerror", out)
        self.assertNotIn("javascript:", out)

    def test_markdown_javascript_link_dropped(self):
        self.assertNotIn("javascript:", render("[x](javascript:alert(1))"))


class PathTests(unittest.TestCase):
    def test_relative_paths_rewritten_external_left(self):
        body = ('<img src="a/b.png"><a href="x.md">x</a><a href="https://e.com">e</a>'
                '<a href="#top">t</a><source srcset="c.svg">')
        with tempfile.TemporaryDirectory() as d:
            out, _ = PR.rewrite_paths(body, d)
        self.assertIn('src="../a/b.png"', out)
        self.assertIn('href="../x.md"', out)
        self.assertIn('href="https://e.com"', out)
        self.assertIn('href="#top"', out)
        self.assertIn('srcset="../c.svg"', out)

    def test_dotfile_path_keeps_dot(self):
        out, _ = PR.rewrite_paths('<a href=".github/x.md">x</a>', tempfile.gettempdir())
        self.assertIn('href="../.github/x.md"', out)

    def test_missing_file_reported(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "ok.png").write_bytes(b"x")
            _, missing = PR.rewrite_paths('<img src="ok.png"><img src="gone.png">', d)
        self.assertEqual(missing, ["gone.png"])


class RunTests(unittest.TestCase):
    def test_run_warns_on_missing_file_and_banned_words(self):
        with tempfile.TemporaryDirectory() as d:
            readme = os.path.join(d, "README.md")
            Path(readme).write_text("# T\n\n![i](nope.png) This is hostile.\n\n[a](#nowhere)\n", encoding="utf-8")
            out = os.path.join(d, "preview", "readme.html")
            info, warnings = PR.run(readme, out)
            self.assertTrue(os.path.exists(out))
            html_text = Path(out).read_text(encoding="utf-8")
        joined = "\n".join(warnings)
        self.assertIn("missing local file referenced: nope.png", joined)
        self.assertIn("hostile", joined)
        self.assertIn("#nowhere", joined)
        self.assertEqual(info["headings"], 1)
        self.assertEqual(info["images"], 1)
        self.assertIn("prefers-color-scheme", html_text)
        self.assertNotIn("<script", html_text)

    def test_clean_readme_has_no_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "pic.png").write_bytes(b"x")
            Path(d, "README.md").write_text("# T\n\n![i](pic.png)\n", encoding="utf-8")
            _, warnings = PR.run(os.path.join(d, "README.md"), os.path.join(d, "preview", "r.html"))
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()

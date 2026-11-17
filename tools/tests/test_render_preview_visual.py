"""2.17.0: branding, charts and flowcharts on the HTML preview. Offline only."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_render_preview as base

SCRIPT = Path(base.ROOT) / "skill-source" / "adversary" / "versions" / "2.17.0" / "scripts" / "render_preview.py"
spec = importlib.util.spec_from_file_location("render_preview_217", SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

FLOW = {
    "title": "Retry loop",
    "nodes": [
        {"id": "a", "text": "Request sent", "kind": "start"},
        {"id": "b", "text": "Did it work?", "kind": "decision"},
        {"id": "c", "text": "Show receipt", "kind": "ok"},
        {"id": "d", "text": "Retry with no limit", "kind": "bad"},
    ],
    "edges": [["a", "b"], ["b", "c", "yes"], ["b", "d", "no"], ["d", "b", "again"]],
}


def render(findings, overview=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pr = root / "PR-1"
        pr.mkdir()
        (pr / "diff.patch").write_text(base.DIFF, encoding="utf-8")
        (pr / "pr.json").write_text(json.dumps({"provider": "ado", "prId": 1, "title": "t"}), encoding="utf-8")
        for f in findings:
            f.setdefault("filePath", "/src/orders/Invoice.kt")
            f.setdefault("severity", "P2")
            f.setdefault("summary", "s")
            f.setdefault("ruleSet", "r")
        doc = {"prId": 1, "status": "ok", "findings": findings}
        if overview is not None:
            doc["overview"] = overview
        (pr / "findings.json").write_text(json.dumps(doc), encoding="utf-8")
        out = subprocess.run([sys.executable, str(SCRIPT), str(root), "1", "--version", "2.17.0"],
                             capture_output=True, text=True)
        return out.stdout + out.stderr, (root / "preview.html").read_text(encoding="utf-8")


class Branding(unittest.TestCase):
    def test_header_footer_and_title(self):
        _out, page = render([base.finding(1, 12)])
        self.assertIn('class="brand"', page)
        self.assertIn("AdversaryPR</span>", page)
        self.assertIn("v2.17.0", page)
        self.assertIn('class="brand-foot"', page)
        self.assertIn("<title>AdversaryPR v2.17.0 preview</title>", page)
        self.assertIn("currentColor", page)  # logo follows light and dark mode

    def test_branding_is_not_in_the_comment_text(self):
        _out, page = render([base.finding(1, 12)])
        raw = page.split("Exact text that will be posted")[1].split("</pre>")[0]
        self.assertNotIn("adversarypr.com", raw)


class Charts(unittest.TestCase):
    def test_severity_and_file_charts(self):
        _out, page = render([base.finding(1, 12, severity="P1"), base.finding(2, 12, severity="P3")])
        self.assertIn("Findings by severity", page)
        self.assertIn("Where the findings are", page)
        self.assertIn("P1 &middot; 1", page)

    def test_no_charts_without_findings(self):
        _out, page = render([])
        self.assertNotIn("Findings by severity", page)


class Flows(unittest.TestCase):
    def test_finding_flow_draws_svg_with_every_node_and_label(self):
        out, page = render([base.finding(1, 12, flow=FLOW)])
        self.assertNotIn("WARNING", out)
        self.assertIn('class="flowsvg"', page)
        for text in ("Request sent", "Did it work?", "Show receipt", "Retry with no limit", "yes", "again"):
            self.assertIn(text, page)
        self.assertIn("k-decision", page)

    def test_flow_text_is_escaped(self):
        flow = {"nodes": [{"id": "a", "text": "<script>alert(1)</script>"}], "edges": []}
        _out, page = render([base.finding(1, 12, flow=flow)])
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("&lt;script&gt;", page)

    def test_overview_shows_above_findings(self):
        out, page = render([base.finding(1, 12)], overview=dict(FLOW, title="How it works"))
        self.assertNotIn("WARNING", out)
        self.assertLess(page.index("How the change works"), page.index('<table class="index">'))

    def test_bad_flows_warn_and_are_skipped(self):
        cases = {
            "unknown edge": {"nodes": [{"id": "a", "text": "a"}], "edges": [["a", "z"]]},
            "duplicate id": {"nodes": [{"id": "a", "text": "a"}, {"id": "a", "text": "b"}]},
            "too many": {"nodes": [{"id": str(i), "text": "n"} for i in range(15)]},
            "no nodes": {"nodes": []},
        }
        for name, flow in cases.items():
            with self.subTest(name):
                out, page = render([base.finding(1, 12, flow=flow)])
                self.assertIn("WARNING #1:", out)
                self.assertNotIn('class="flowsvg"', page)

    def test_cycle_and_self_loop_do_not_hang(self):
        flow = {"nodes": [{"id": "a", "text": "a"}, {"id": "b", "text": "b"}],
                "edges": [["a", "b"], ["b", "a"], ["b", "b"]]}
        out, page = render([base.finding(1, 12, flow=flow)])
        self.assertNotIn("WARNING", out)
        self.assertIn('class="flowsvg"', page)

    def test_flow_never_changes_the_posted_content(self):
        _o1, with_flow = render([base.finding(1, 12, flow=FLOW)])
        raw = with_flow.split("Exact text that will be posted")[1].split("</pre>")[0]
        self.assertNotIn("Request sent", raw)


if __name__ == "__main__":
    unittest.main()

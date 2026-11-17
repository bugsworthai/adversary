"""2.18.0: overview flowchart with pinned findings, and PDF/PNG export. Offline only."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_render_preview as base

SCRIPT = Path(base.ROOT) / "skill-source" / "adversary" / "versions" / "2.18.0" / "scripts" / "render_preview.py"
spec = importlib.util.spec_from_file_location("render_preview_218", SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

OVERVIEW = {
    "title": "How checkout works",
    "nodes": [
        {"id": "a", "text": "User taps Pay", "kind": "start"},
        {"id": "b", "text": "RetryPolicy decides", "kind": "decision", "findings": [1]},
        {"id": "c", "text": "PaymentApi.charge()", "findings": [2]},
    ],
    "edges": [["a", "b"], ["b", "c", "yes"], ["c", "b", "failed"]],
}


def render(overview, extra=(), n=2):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pr = root / "PR-1"
        pr.mkdir()
        (pr / "diff.patch").write_text(base.DIFF, encoding="utf-8")
        (pr / "pr.json").write_text(json.dumps({"provider": "ado", "prId": 1, "title": "t"}), encoding="utf-8")
        fs = [base.finding(i + 1, 12, filePath="/src/orders/Invoice.kt", severity="P1" if i == 0 else "P3",
                           summary="s", ruleSet="r") for i in range(n)]
        doc = {"prId": 1, "status": "ok", "findings": fs}
        if overview is not None:
            doc["overview"] = overview
        (pr / "findings.json").write_text(json.dumps(doc), encoding="utf-8")
        out = subprocess.run([sys.executable, str(SCRIPT), str(root), "1", "--version", "2.18.0", *extra],
                             capture_output=True, text=True)
        return out.stdout + out.stderr, (root / "preview.html").read_text(encoding="utf-8"), root


class Overview(unittest.TestCase):
    def test_pins_link_to_findings_and_carry_severity(self):
        out, page, _ = render(OVERVIEW)
        self.assertNotIn("WARNING", out)
        self.assertIn('href="#f-1-1"', page)
        self.assertIn("P1 #1", page)
        self.assertIn("P3 #2", page)
        self.assertIn('class="pin p1"', page)
        self.assertIn("Badges mark the steps", page)

    def test_missing_overview_warns(self):
        out, _page, _ = render(None)
        self.assertIn("WARNING PR 1: no overview flowchart", out)

    def test_pin_to_unknown_finding_warns_but_still_draws(self):
        ov = json.loads(json.dumps(OVERVIEW))
        ov["nodes"][0]["findings"] = [9]
        out, page, _ = render(ov)
        self.assertIn("finding 9, which does not exist", out)
        self.assertIn('class="flowsvg"', page)

    def test_page_has_export_controls_and_print_css(self):
        _out, page, _ = render(OVERVIEW)
        self.assertIn('id="pdf"', page)
        self.assertIn("flow-png", page)
        self.assertIn("@media print", page)
        self.assertIn("data-h", page)

    def test_branding_and_flow_stay_out_of_posted_text(self):
        _out, page, _ = render(OVERVIEW)
        raw = page.split("Exact text that will be posted")[1].split("</pre>")[0]
        self.assertNotIn("adversarypr.com", raw)
        self.assertNotIn("User taps Pay", raw)


@unittest.skipUnless(RP.find_browser(), "no Chromium-based browser installed")
class Export(unittest.TestCase):
    def test_pdf_and_png_are_written(self):
        out, _page, root = render(OVERVIEW, extra=("--pdf", "--png"))
        self.assertNotIn("export:", out)
        self.assertIn("PDF:", out)
        self.assertIn("PNG:", out)


class NoBrowser(unittest.TestCase):
    def test_export_without_a_browser_says_what_to_do(self):
        saved = RP.BROWSERS
        RP.BROWSERS = ["definitely-not-a-browser"]
        try:
            err = RP.export_page(Path("x.html"), "pdf", Path("x.pdf"))
        finally:
            RP.BROWSERS = saved
        self.assertIn("Save as PDF", err)


if __name__ == "__main__":
    unittest.main()

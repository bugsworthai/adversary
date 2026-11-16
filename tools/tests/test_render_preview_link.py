"""2.14.0: the preview script prints a clickable file:// link on its own line."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_render_preview as base

SCRIPT = Path(base.ROOT) / "skill-source" / "adversary" / "versions" / "2.14.0" / "scripts" / "render_preview.py"


class FileLink(unittest.TestCase):
    def test_prints_file_url_on_its_own_line(self):
        with tempfile.TemporaryDirectory(prefix="run with space ") as tmp:
            root = Path(tmp)
            pr = root / "PR-1"
            pr.mkdir()
            (pr / "diff.patch").write_text(base.DIFF, encoding="utf-8")
            (pr / "pr.json").write_text(json.dumps({"provider": "ado", "prId": 1, "title": "t"}), encoding="utf-8")
            f = base.finding(filePath="/src/orders/Invoice.kt", severity="P2", summary="s", ruleSet="r")
            (pr / "findings.json").write_text(json.dumps({"prId": 1, "status": "ok", "findings": [f]}), encoding="utf-8")
            out = subprocess.run([sys.executable, str(SCRIPT), str(root), "1", "--version", "2.14.0"],
                                 capture_output=True, text=True).stdout.splitlines()
            url = (root / "preview.html").resolve().as_uri()
            self.assertIn(url, out)
            self.assertTrue(url.startswith("file:///"))
            self.assertIn("%20", url)  # the space is encoded, so the link stays whole


if __name__ == "__main__":
    unittest.main()

"""Offline tests for 2.26.0: a PR whose files the target branch moved or removed. Nothing here touches the network."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill-source" / "adversary" / "versions" / "2.26.0" / "scripts" / "render_preview.py"
spec = importlib.util.spec_from_file_location("render_preview_226", SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

META = {"targetBranch": "main", "url": "https://github.com/acme/orders-api/pull/101",
        "freshness": {"status": "moved", "behindBy": 12, "overlapFiles": [], "conflictFiles": [],
                      "movedFiles": [{"from": "src/orders/Service.py", "to": "src/billing/orders/Service.py"}],
                      "deletedFiles": ["src/orders/legacy.py"], "overlapChecked": True, "source": "git", "note": ""}}


class Moved(unittest.TestCase):
    def test_status_is_known(self):
        self.assertIn("moved", RP.FIT_STATUSES)

    def test_text_names_moved_and_removed_files(self):
        t = RP.fit_text(META)
        self.assertIn("src/orders/Service.py to src/billing/orders/Service.py", t)
        self.assertIn("removed: src/orders/legacy.py", t)

    def test_next_step_says_comments_may_not_apply(self):
        self.assertIn("will not apply", RP.fit_next(META))

    def test_bad_entries_are_ignored(self):
        fr = dict(META["freshness"], movedFiles=["junk", {"from": "a"}], deletedFiles=[])
        self.assertEqual(RP.moved_text(fr), "")
        self.assertIn("see pr.json", RP.fit_text(dict(META, freshness=fr)))

    def test_long_lists_are_capped_at_five(self):
        fr = dict(META["freshness"], movedFiles=[], deletedFiles=["f%d" % i for i in range(9)])
        t = RP.moved_text(fr)
        self.assertIn("f4", t)
        self.assertNotIn("f5", t)

    def test_older_statuses_still_read_the_same(self):
        self.assertEqual(RP.fit_text({"targetBranch": "main", "freshness": {"status": "current"}}), "Up to date with main")


if __name__ == "__main__":
    unittest.main()

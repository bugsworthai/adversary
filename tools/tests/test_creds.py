"""2.15.0: per-organization credentials (creds.py)."""
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill-source" / "adversary" / "versions" / "2.15.0" / "scripts" / "creds.py"
spec = importlib.util.spec_from_file_location("creds", SCRIPT)
creds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creds)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "creds.json"
        os.environ["ADVERSARY_CREDS_FILE"] = str(self.file)

    def tearDown(self):
        os.environ.pop("ADVERSARY_CREDS_FILE", None)
        self.tmp.cleanup()

    def write(self, obj):
        self.file.write_text(json.dumps(obj), encoding="utf-8")

    def run_cmd(self, *argv, stdin=None):
        out = io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(stdin or "")
        try:
            with redirect_stdout(out):
                code = creds.main(list(argv))
        finally:
            sys.stdin = old
        return code, out.getvalue()


class Matching(Base):
    def test_org_match_is_case_insensitive(self):
        self.write({"profiles": [{"org": "Contoso", "username": "a", "pat": "p1"}]})
        self.assertEqual(self.run_cmd("basic", "--org", "contoso"), (0, "a:p1\n"))

    def test_most_specific_wins(self):
        self.write({"profiles": [
            {"org": "Contoso", "username": "org", "pat": "po"},
            {"org": "Contoso", "project": "Shop", "username": "proj", "pat": "pp"},
            {"org": "Contoso", "repo": "orders-api", "username": "repo", "pat": "pr"}]})
        self.assertEqual(self.run_cmd("who", "--org", "Contoso", "--project", "Shop", "--repo", "ios-app")[1].splitlines()[0], "proj")
        self.assertEqual(self.run_cmd("who", "--org", "Contoso", "--project", "Shop", "--repo", "orders-api")[1].splitlines()[0], "repo")
        self.assertEqual(self.run_cmd("who", "--org", "Contoso", "--project", "Other")[1].splitlines()[0], "org")

    def test_other_org_does_not_match(self):
        self.write({"profiles": [{"org": "Contoso", "username": "a", "pat": "p1"}]})
        self.assertEqual(self.run_cmd("who", "--org", "Fabrikam")[0], 1)

    def test_old_single_pat_file_is_the_fallback(self):
        self.write({"username": "old", "pat": "oldpat"})
        self.assertEqual(self.run_cmd("basic", "--org", "Anything"), (0, "old:oldpat\n"))
        self.write({"username": "old", "pat": "oldpat", "profiles": [{"org": "Contoso", "username": "c", "pat": "cp"}]})
        self.assertEqual(self.run_cmd("basic", "--org", "Contoso")[1], "c:cp\n")
        self.assertEqual(self.run_cmd("basic", "--org", "Elsewhere")[1], "old:oldpat\n")

    def test_missing_file_matches_nothing(self):
        self.assertEqual(self.run_cmd("who", "--org", "Contoso")[0], 1)


class Writing(Base):
    def test_add_reads_the_pat_from_stdin_and_locks_the_file(self):
        code, out = self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="secret1\n")
        self.assertEqual(code, 0)
        self.assertNotIn("secret1", out)
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
        self.assertEqual(self.run_cmd("basic", "--org", "Contoso")[1], "a:secret1\n")

    def test_add_replaces_the_same_profile(self):
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="one\n")
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="two\n")
        self.assertEqual(len(json.loads(self.file.read_text())["profiles"]), 1)
        self.assertEqual(self.run_cmd("basic", "--org", "Contoso")[1], "a:two\n")

    def test_add_keeps_the_old_single_pat(self):
        self.write({"username": "old", "pat": "oldpat"})
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="new\n")
        self.assertEqual(self.run_cmd("basic", "--org", "Other")[1], "old:oldpat\n")

    def test_list_never_shows_a_pat(self):
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="topsecret\n")
        out = self.run_cmd("list")[1]
        self.assertIn("pat=***", out)
        self.assertNotIn("topsecret", out)

    def test_who_never_shows_a_pat(self):
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="topsecret\n")
        self.assertNotIn("topsecret", self.run_cmd("who", "--org", "Contoso")[1])

    def test_remove(self):
        self.run_cmd("add", "--org", "Contoso", "--username", "a", stdin="x\n")
        self.assertEqual(self.run_cmd("remove", "--org", "Contoso")[0], 0)
        self.assertEqual(self.run_cmd("who", "--org", "Contoso")[0], 1)

    def test_empty_pat_is_refused(self):
        self.assertEqual(self.run_cmd("add", "--org", "Contoso", stdin="\n")[0], 2)


class GitHubHints(Base):
    def test_map_and_lookup(self):
        self.run_cmd("github-map", "--owner", "acme", "--gh-user", "alice")
        self.assertEqual(self.run_cmd("github-user", "--owner", "ACME"), (0, "alice\n"))
        self.assertEqual(self.run_cmd("github-user", "--owner", "other")[0], 1)


if __name__ == "__main__":
    unittest.main()

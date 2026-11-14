"""Offline tests for the client telemetry script. Nothing here touches the network."""
import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[2] / "skill-source" / "adversary" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import telemetry as T  # noqa: E402
import telemetry_constants as C  # noqa: E402

ALLOWED = {"schema", "event", "version", "dry_run", "html", "model", "version_pinned"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {"HOME": self.tmp.name, "USERPROFILE": self.tmp.name}
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)
        for k in (C.ENV_TELEMETRY, C.ENV_DO_NOT_TRACK):
            os.environ.pop(k, None)

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = T.main(list(argv))
        return code, out.getvalue()


class ConsentTests(Base):
    def test_default_is_ask(self):
        self.assertEqual(self.run_main("status"), (0, "ask\n"))

    def test_set_on_off(self):
        self.run_main("set", "on")
        self.assertEqual(self.run_main("status")[1], "on\n")
        self.run_main("set", "off")
        self.assertEqual(self.run_main("status")[1], "off\n")

    def test_state_file_holds_only_consent(self):
        self.run_main("set", "on")
        self.assertEqual(json.loads(T.state_file().read_text()), {"consent": "on"})

    def test_corrupt_file_means_ask(self):
        T.state_file().parent.mkdir(parents=True)
        T.state_file().write_text("not json")
        self.assertEqual(T.read_consent(), "ask")
        T.state_file().write_text(json.dumps({"consent": "maybe"}))
        self.assertEqual(T.read_consent(), "ask")

    def test_env_opt_outs_force_off_and_never_ask(self):
        for var, val in (("ADVERSARY_TELEMETRY", "0"), ("DO_NOT_TRACK", "1")):
            with mock.patch.dict(os.environ, {var: val}):
                self.assertEqual(T.read_consent(), "off")
                self.run_main("set", "on")
                self.assertEqual(T.read_consent(), "off")

    def test_permissions(self):
        self.run_main("set", "on")
        self.assertEqual(stat.S_IMODE(os.stat(T.state_file().parent).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(T.state_file()).st_mode), 0o600)


class PayloadTests(Base):
    def test_exact_allowlist(self):
        p = T.build_payload("2.5.0", True, True, "haiku", True)
        self.assertEqual(set(p), ALLOWED)
        self.assertEqual(p["version"], "2.5.0")
        self.assertIs(p["dry_run"], True)

    def test_defaults(self):
        p = T.build_payload("2.5.0")
        self.assertEqual((p["dry_run"], p["html"], p["model"], p["version_pinned"]),
                         (False, False, "default", False))

    def test_bad_inputs_rejected(self):
        for v in ("2.5", "v2.5.0", "2.5.0\n", "2.5.0-x", "", "../x"):
            with self.assertRaises(ValueError):
                T.build_payload(v)
        with self.assertRaises(ValueError):
            T.build_payload("2.5.0", model="gpt")

    def test_preview_prints_payload_and_sends_nothing(self):
        with mock.patch.object(T.urllib.request, "urlopen") as uo:
            code, out = self.run_main("preview", "--version", "2.5.0", "--dry-run", "--model", "opus")
        uo.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), T.build_payload("2.5.0", True, False, "opus", False))


class SendTests(Base):
    def test_send_without_consent_does_nothing(self):
        for setup in (lambda: None, lambda: self.run_main("set", "off")):
            setup()
            with mock.patch.object(T.urllib.request, "urlopen") as uo:
                code, out = self.run_main("send", "--version", "2.5.0")
            uo.assert_not_called()
            self.assertEqual((code, out), (0, ""))

    def test_send_with_env_off_does_nothing(self):
        self.run_main("set", "on")
        with mock.patch.dict(os.environ, {"ADVERSARY_TELEMETRY": "0"}), \
                mock.patch.object(T.urllib.request, "urlopen") as uo:
            self.run_main("send", "--version", "2.5.0")
        uo.assert_not_called()

    def test_send_posts_same_payload_as_preview(self):
        self.run_main("set", "on")
        captured = {}

        def fake(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            captured["timeout"] = timeout
            captured["method"] = req.get_method()
            captured["url"] = req.full_url
            return io.BytesIO(b"")

        args = ("--version", "2.5.0", "--html", "--model", "sonnet", "--pinned")
        with mock.patch.object(T.urllib.request, "urlopen", fake):
            code, out = self.run_main("send", *args)
        _, preview = self.run_main("preview", *args)
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(captured["body"], json.loads(preview))
        self.assertEqual(set(captured["body"]), ALLOWED)
        self.assertEqual(captured["timeout"], 2)
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], C.ENDPOINT_URL)

    def test_send_swallows_errors_silently(self):
        self.run_main("set", "on")
        for exc in (OSError("boom"), TimeoutError(), ValueError("x")):
            with mock.patch.object(T.urllib.request, "urlopen", side_effect=exc):
                self.assertEqual(self.run_main("send", "--version", "2.5.0"), (0, ""))

    def test_send_bad_args_still_exit_zero(self):
        self.run_main("set", "on")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.run_main("send", "--version", "bad"), (0, ""))
            self.assertEqual(self.run_main("send", "--nonsense"), (0, ""))
        self.assertEqual(err.getvalue().count("Traceback"), 0)

    def test_unreachable_url_is_quick_and_silent(self):
        self.run_main("set", "on")
        with mock.patch.object(C, "ENDPOINT_URL", "http://127.0.0.1:9/collect"):
            start = time.time()
            self.assertEqual(self.run_main("send", "--version", "2.5.0"), (0, ""))
        self.assertLess(time.time() - start, 3)


if __name__ == "__main__":
    unittest.main()

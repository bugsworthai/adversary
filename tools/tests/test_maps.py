"""Offline tests for the 2.25.0 maps, summary and listening panel. Nothing here touches the network."""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skill-source" / "adversary" / "versions" / "2.25.0" / "scripts" / "render_preview.py"
SAMPLE = ROOT / "assets" / "sample-run" / "PR-101"
spec = importlib.util.spec_from_file_location("render_preview_225", SCRIPT)
RP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RP)

SEV = {1: "P1", 2: "P2"}


def node(i, **k):
    return dict(id=i, title=i.upper(), **k)


def good():
    return {"nodes": [node("a"), node("b", changed=True, findings=[1]), node("c")],
            "edges": [{"from": "a", "to": "b", "caption": "A calls B."},
                      {"from": "b", "to": "c", "label": "next", "caption": "B calls C."},
                      {"from": "c", "to": "b", "caption": "C loops back.", "bad": True}]}


class CheckMap(unittest.TestCase):
    def check(self, m):
        problems = []
        return RP.check_map(m, "t", problems, SEV), problems

    def test_good_map(self):
        m, problems = self.check(good())
        self.assertEqual(problems, [])
        self.assertEqual(len(m["edges"]), 3)
        self.assertEqual(m["nodes"][1]["pins"], [1])

    def test_rejects(self):
        for mutate in (
            lambda m: m["nodes"].pop(),  # edges now name a missing node
            lambda m: m["edges"].append({"from": "a", "to": "a", "caption": "x"}),
            lambda m: m["nodes"].append(node("a")),
            lambda m: m["nodes"][0].update(title="x" * 40),
            lambda m: m["edges"][0].update(caption=""),
            lambda m: m["edges"][0].update(caption="y" * 130),
            lambda m: m["nodes"][1].update(findings=[9]),
            lambda m: m["nodes"][0].update(rows=["r"] * 9),
        ):
            m = good()
            mutate(m)
            cleaned, problems = self.check(m)
            self.assertTrue(problems, "expected a problem")
            if "points at finding" not in json.dumps(problems):
                self.assertIsNone(cleaned)

    def test_too_many_nodes(self):
        m = {"nodes": [node("n%d" % i) for i in range(11)], "edges": [{"from": "n0", "to": "n1", "caption": "x"}]}
        self.assertIsNone(self.check(m)[0])


class Layout(unittest.TestCase):
    def test_columns_and_loop(self):
        laid = RP.layout_map(RP.check_map(good(), "t", [], SEV), SEV)
        xs = {n["id"]: n["x"] for n in laid["nodes"]}
        self.assertLess(xs["a"], xs["b"])
        self.assertLess(xs["b"], xs["c"])
        for n in laid["nodes"]:
            self.assertGreaterEqual(n["x"], 0)
            self.assertLessEqual(n["x"] + n["w"], laid["w"])
            self.assertLessEqual(n["y"] + n["h"], laid["h"])
        loop = laid["edges"][2]
        self.assertTrue(loop["dash"])
        self.assertGreater(max(p[1] for p in loop["p"]), max(n["y"] + n["h"] for n in laid["nodes"]) - 1)
        self.assertEqual(laid["nodes"][1]["badges"], [["P1", 1]])
        self.assertTrue(laid["nodes"][1]["hot"])


class Page(unittest.TestCase):
    def run_dir(self, mutate=None):
        d = Path(tempfile.mkdtemp())
        shutil.copytree(SAMPLE, d / "PR-101")
        f = json.loads((d / "PR-101" / "findings.json").read_text())
        f["summary"] = "This change retries a failed payment. It touches money."
        f["maps"] = {"dataflow": good(), "architecture": {}}
        f["maps"]["dataflow"]["nodes"][1]["findings"] = [1]
        if mutate:
            mutate(f)
        (d / "PR-101" / "findings.json").write_text(json.dumps(f))
        return d

    def render(self, d):
        prs = RP.collect(d, [])
        problems = []
        return RP.render_page(prs, "2.25.0", d, problems), problems

    def test_page_has_maps_listen_and_watermark(self):
        page, problems = self.render(self.run_dir())
        self.assertEqual(problems, [])
        for needle in ('class="maps"', 'class="listen"', 'class="mtext"', 'class="wm"', "window.__ADV_LOGO", "speechSynthesis", 'class="brandt"'):
            self.assertIn(needle, page)
        self.assertEqual(page.count("</script>"), page.count("<script"))

    def test_missing_maps_and_summary_warn(self):
        def drop(f):
            f.pop("maps")
            f.pop("summary")
        page, problems = self.render(self.run_dir(drop))
        self.assertTrue(any("maps" in p for p in problems))
        self.assertTrue(any("summary" in p for p in problems))
        self.assertNotIn('class="maps"', page)

    def test_empty_maps_is_allowed(self):
        _, problems = self.render(self.run_dir(lambda f: f.update(maps={})))
        self.assertFalse(any("maps" in p for p in problems))

    def test_script_breakout_is_escaped(self):
        def evil(f):
            f["maps"]["dataflow"]["nodes"][0]["title"] = "</script><b>x"
        page, _ = self.render(self.run_dir(evil))
        self.assertNotIn("</script><b>", page)

    def test_summary_sentences(self):
        d = self.run_dir()
        pr = RP.collect(d, [])[0]
        sev = {f["n"]: f["severity"] for f in pr["findings"]}
        out = RP.summary_sentences(pr, sev, [])
        self.assertTrue(out[0].startswith("PR 101:"))
        self.assertTrue(any(s.startswith("Impact on the codebase: 3 of 5") for s in out))
        self.assertTrue(any(s.startswith("Finding 1, P1") for s in out))
        self.assertTrue(all(s.rstrip()[-1] in ".!?" for s in out))


if __name__ == "__main__":
    unittest.main()

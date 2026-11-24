#!/usr/bin/env python3
"""Make the HTML-preview screenshots used by the README and the website.

It renders assets/sample-run (a made-up checkout-retry review) with the newest version's
render_preview.py, then screenshots the page with an installed Chrome, Edge, Brave or Chromium
at 2x. The run folder line (a local path) is removed first.

  python3 tools/make_screenshots.py            # writes assets/html-preview-v2.png, html-flow-v2.png and html-maps-v1.png
  python3 tools/make_screenshots.py --out DIR  # write them somewhere else

Standard library only; Python 3.8+.
"""
import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skill-source" / "adversary"


def newest_version():
    names = [p.name for p in (SKILL / "versions").iterdir() if p.is_dir()]
    return max(names, key=lambda v: tuple(int(x) for x in v.split(".")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "assets"), help="folder for the PNGs")
    args = ap.parse_args()
    version = newest_version()
    spec = importlib.util.spec_from_file_location("render_preview", SKILL / "versions" / version / "scripts" / "render_preview.py")
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    browser = rp.find_browser()
    if not browser:
        sys.exit("No Chrome, Edge, Brave or Chromium found.")

    work = Path(tempfile.mkdtemp(prefix="adversary-shots-"))
    run = work / "run"
    shutil.copytree(ROOT / "assets" / "sample-run", run)
    rp.main([str(run), "101", "--version", version, "--no-pdf"])
    html = (run / "preview.html").read_text(encoding="utf-8")
    html = re.sub(r'<p class="meta">Run folder:.*?</p>', "", html)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    shots = [("html-preview-v2.png", 1280, 1330, ".scorecard,figure.flow,section.pr > .chart-title,figure.flow + p.meta,p.lede,.finding ~ .finding,details.dropped,.listen,.maps{display:none!important}"),
             ("html-flow-v2.png", 1100, 1110, ".finding,.bar,.brand-foot,table.index,details,.chart-row,.charts,p.lede,.listen,.maps{display:none!important}"),
             ("html-maps-v1.png", 1100, 770, "main > *:not(section.pr),.scorecard,.listen,figure.flow,.finding,table.index,details,section.pr > p,h2,.bar,.brand-foot,section.pr > .chart-title,.mbar,.maps > .meta,.mtext{display:none!important}main{padding-top:14px}")]
    for name, w, h, css in shots:
        page = work / ("page-" + name + ".html")
        page.write_text(html.replace("</head>", "<style>%s</style></head>" % css) if css else html, encoding="utf-8")
        profile = tempfile.mkdtemp(prefix="adversary-chrome-")
        target = out_dir / name
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                        "--user-data-dir=" + profile, "--window-size=%d,%d" % (w, h), "--virtual-time-budget=4000",
                        "--screenshot=" + str(target), page.as_uri() + "#still"], capture_output=True, timeout=120)
        shutil.rmtree(profile, ignore_errors=True)
        print(target, "OK" if target.exists() else "FAILED")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

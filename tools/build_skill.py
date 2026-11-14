#!/usr/bin/env python3
"""Check, package, and optionally install the AdversaryPR skill.

Run from anywhere:
    python3 tools/build_skill.py            # check, then write adversary.skill
    python3 tools/build_skill.py --check    # check only
    python3 tools/build_skill.py --install  # check, package, and copy to ~/.claude/skills/adversary

Checks:
  - SKILL.md frontmatter is something an org skill upload accepts (allowed keys,
    name, description of 1024 characters or fewer, no angle brackets).
  - The "Available versions" table, the "Latest version" line, the release
    notes, and the versions/ folders all agree.
  - Released versions are frozen: every version folder in the last-built
    adversary.skill must be byte-for-byte unchanged in the source. Pass
    --allow-change X.Y.Z only if you really mean to change a released version.
  - No nested SKILL.md, and every bundled .py file compiles.

Standard library only, Python 3.8+.
"""
from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "skill-source" / "adversary"
PACKAGE = ROOT / "adversary.skill"
INSTALL = Path.home() / ".claude" / "skills" / "adversary"
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SKIP = {".DS_Store", "__pycache__"}


def vkey(v: str):
    return tuple(int(p) for p in v.split("."))


def source_files(base: Path):
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(part in SKIP for part in p.parts) and p.suffix != ".pyc":
            yield p


def check(allow_change: set) -> list:
    errors = []
    skill_md = SOURCE / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")

    # Frontmatter
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["SKILL.md has no frontmatter block"]
    fm = {}
    for line in m.group(1).splitlines():
        if line.strip() and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        errors.append("frontmatter keys an org upload rejects: %s" % ", ".join(sorted(extra)))
    if fm.get("name") != SOURCE.name:
        errors.append("frontmatter name %r must be %r" % (fm.get("name"), SOURCE.name))
    desc = fm.get("description", "")
    if not desc:
        errors.append("frontmatter description is empty")
    if len(desc) > 1024:
        errors.append("description is %d characters (max 1024)" % len(desc))
    if "<" in desc or ">" in desc:
        errors.append("description contains < or >")

    # Versions: table, latest line, release notes, folders
    table = re.findall(r"^\|\s*\**(\d+\.\d+\.\d+)\**\s*(\(latest\))?\s*\|", text, re.M)
    in_table = [v for v, _ in table]
    marked = [v for v, latest in table if latest]
    latest_line = re.search(r"\*\*Latest version: (\d+\.\d+\.\d+)\*\*", text)
    folders = sorted(p.name for p in (SOURCE / "versions").iterdir() if p.is_dir())
    notes = set(re.findall(r"^### (\d+\.\d+\.\d+) ", text, re.M))
    if set(in_table) != set(folders):
        errors.append("versions table %s doesn't match versions/ folders %s" % (sorted(in_table, key=vkey), folders))
    highest = max(folders, key=vkey) if folders else None
    if not latest_line or latest_line.group(1) != highest:
        errors.append("'Latest version' line must name the highest version, %s" % highest)
    if marked != [highest]:
        errors.append("exactly one table row, %s, must be marked (latest); found %s" % (highest, marked))
    missing_notes = set(folders) - notes
    if missing_notes:
        errors.append("no release-notes heading for %s" % ", ".join(sorted(missing_notes, key=vkey)))
    for v in folders:
        if not (SOURCE / "versions" / v / "instructions.md").is_file():
            errors.append("versions/%s/instructions.md is missing" % v)

    # Nested SKILL.md, Python syntax
    for p in source_files(SOURCE):
        if p.name == "SKILL.md" and p != skill_md:
            errors.append("nested SKILL.md: %s" % p.relative_to(SOURCE))
        if p.suffix == ".py":
            try:
                py_compile.compile(str(p), cfile=str(Path(tempfile.gettempdir()) / "adversary_check.pyc"), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append("%s doesn't compile: %s" % (p.relative_to(SOURCE), exc.msg))

    # Released versions are frozen
    if PACKAGE.is_file():
        with zipfile.ZipFile(PACKAGE) as z:
            released = {}
            for name in z.namelist():
                parts = name.split("/")
                if len(parts) > 3 and parts[1] == "versions" and not name.endswith("/"):
                    released.setdefault(parts[2], {})["/".join(parts[3:])] = z.read(name)
        for v, files in sorted(released.items()):
            if v in allow_change:
                continue
            vdir = SOURCE / "versions" / v
            if not vdir.is_dir():
                errors.append("released version %s was deleted from versions/" % v)
                continue
            now = {str(p.relative_to(vdir)).replace("\\", "/"): p.read_bytes() for p in source_files(vdir)}
            changed = sorted(f for f in set(files) | set(now) if files.get(f) != now.get(f))
            if changed:
                errors.append(
                    "released version %s changed (%s). Make a new version instead, or pass --allow-change %s"
                    % (v, ", ".join(changed), v)
                )
    return errors


def package() -> None:
    tmp = PACKAGE.with_suffix(".skill.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in source_files(SOURCE):
            z.write(p, Path(SOURCE.name) / p.relative_to(SOURCE))
    tmp.replace(PACKAGE)


def install() -> None:
    if INSTALL.exists():
        shutil.rmtree(INSTALL)
    shutil.copytree(SOURCE, INSTALL, ignore=shutil.ignore_patterns(*SKIP, "*.pyc"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="check only; don't write the package")
    ap.add_argument("--install", action="store_true", help="also copy the skill to %s" % INSTALL)
    ap.add_argument("--allow-change", action="append", default=[], metavar="X.Y.Z",
                    help="let a released version differ from the last package (rarely right)")
    args = ap.parse_args()

    errors = check(set(args.allow_change))
    if errors:
        print("Not packaged. Fix these first:")
        for e in errors:
            print("  - " + e)
        return 1
    latest = re.search(r"\*\*Latest version: (\S+)\*\*", (SOURCE / "SKILL.md").read_text(encoding="utf-8")).group(1)
    print("Checks passed (latest version %s)." % latest)
    if args.check:
        return 0
    package()
    print("Wrote %s" % PACKAGE)
    if args.install:
        install()
        print("Installed to %s" % INSTALL)
    return 0


if __name__ == "__main__":
    sys.exit(main())

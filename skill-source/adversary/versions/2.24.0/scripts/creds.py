#!/usr/bin/env python3
"""Per-organization Azure DevOps credentials (and GitHub account hints) for AdversaryPR.

The file is ~/.ado-pr-review-creds.json (override: ADVERSARY_CREDS_FILE), created with owner-only
permissions. Standard library only, Python 3.8+. A PAT is never printed except by `basic`, which is
meant to sit inside a command substitution (curl -u "$(creds.py basic --org X)") so it is not echoed.

File format:
  {"profiles": [{"org": "Contoso", "username": "First.Last", "pat": "..."},
                {"org": "Contoso", "project": "Shop", "username": "First.Last", "pat": "..."},
                {"org": "Fabrikam", "repo": "orders-api", "username": "F.Last", "pat": "..."}],
   "github": {"acme": "alice"}}
The old single-PAT form {"username": "...", "pat": "..."} still works: it is the fallback for any org.

Commands:
  who          --org O [--project P] [--repo R]   username and which profile matched (no PAT)
  basic        --org O [--project P] [--repo R]   "username:pat" for curl -u
  add          --org O [--project P] [--repo R] [--username U]   PAT from a hidden prompt, or stdin
  list                                           profiles, PATs shown as ***
  remove       --org O [--project P] [--repo R]
  github-user  --owner O                         the gh account mapped to that owner, if any
  github-map   --owner O --gh-user U             map a GitHub owner to a gh account
Exit code 1 when nothing matches.
"""
import argparse
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path


def path():
    return Path(os.environ.get("ADVERSARY_CREDS_FILE") or Path.home() / ".ado-pr-review-creds.json")


def load():
    p = path()
    if not p.exists():
        return {"profiles": [], "github": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    profiles = list(data.get("profiles") or [])
    if data.get("pat"):  # the old single-PAT file is the fallback for any organization
        profiles.append({"org": "*", "username": data.get("username", ""), "pat": data["pat"]})
    out = {"profiles": profiles, "github": dict(data.get("github") or {})}
    return out


def save(data):
    p = path()
    body = {"profiles": [x for x in data["profiles"] if x.get("org") != "*"]}
    legacy = [x for x in data["profiles"] if x.get("org") == "*"]
    if legacy:
        body["username"], body["pat"] = legacy[0].get("username", ""), legacy[0]["pat"]
    if data.get("github"):
        body["github"] = data["github"]
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".creds-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _eq(a, b):
    return (a or "").lower() == (b or "").lower()


def match(data, org, project=None, repo=None):
    """The most specific profile for this PR, or None. Specificity: repo > project > org > old fallback."""
    best, best_score = None, -1
    for pr in data["profiles"]:
        po = pr.get("org", "")
        if po == "*":
            score = 0
        elif _eq(po, org):
            score = 1
            if pr.get("project"):
                if not _eq(pr["project"], project):
                    continue
                score += 1
            if pr.get("repo"):
                if not _eq(pr["repo"], repo):
                    continue
                score += 2
            score += 1
        else:
            continue
        if score > best_score:
            best, best_score = pr, score
    return best


def describe(pr):
    if pr.get("org") == "*":
        return "the old single-PAT entry"
    parts = ["org=" + pr["org"]]
    for k in ("project", "repo"):
        if pr.get(k):
            parts.append("%s=%s" % (k, pr[k]))
    return " ".join(parts)


def key(pr):
    return (pr.get("org", "").lower(), (pr.get("project") or "").lower(), (pr.get("repo") or "").lower())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("who", "basic", "add", "remove"):
        s = sub.add_parser(name)
        s.add_argument("--org", required=True)
        s.add_argument("--project")
        s.add_argument("--repo")
        if name == "add":
            s.add_argument("--username")
    sub.add_parser("list")
    g = sub.add_parser("github-user")
    g.add_argument("--owner", required=True)
    m = sub.add_parser("github-map")
    m.add_argument("--owner", required=True)
    m.add_argument("--gh-user", required=True)
    a = ap.parse_args(argv)
    data = load()

    if a.cmd in ("who", "basic"):
        pr = match(data, a.org, a.project, a.repo)
        if not pr:
            return 1
        if a.cmd == "basic":
            print("%s:%s" % (pr.get("username", ""), pr["pat"]))
        else:
            print(pr.get("username", ""))
            print("matched: " + describe(pr))
        return 0
    if a.cmd == "add":
        pat = sys.stdin.readline().strip() if not sys.stdin.isatty() else getpass.getpass("PAT (hidden): ").strip()
        if not pat:
            print("error: no PAT given", file=sys.stderr)
            return 2
        username = a.username or (input("Username: ").strip() if sys.stdin.isatty() else "")
        new = {"org": a.org, "username": username, "pat": pat}
        if a.project:
            new["project"] = a.project
        if a.repo:
            new["repo"] = a.repo
        data["profiles"] = [x for x in data["profiles"] if x.get("org") == "*" or key(x) != key(new)] + [new]
        save(data)
        print("saved: " + describe(new))
        return 0
    if a.cmd == "remove":
        probe = {"org": a.org, "project": a.project, "repo": a.repo}
        before = len(data["profiles"])
        data["profiles"] = [x for x in data["profiles"] if x.get("org") == "*" or key(x) != key(probe)]
        save(data)
        print("removed %d" % (before - len(data["profiles"])))
        return 0 if before != len(data["profiles"]) else 1
    if a.cmd == "list":
        for pr in data["profiles"]:
            print("%s  user=%s  pat=***" % (describe(pr), pr.get("username", "")))
        for owner, user in sorted(data["github"].items()):
            print("github owner=%s  gh-user=%s" % (owner, user))
        return 0
    if a.cmd == "github-user":
        for owner, user in data["github"].items():
            if _eq(owner, a.owner):
                print(user)
                return 0
        return 1
    if a.cmd == "github-map":
        data["github"][a.owner] = a.gh_user
        save(data)
        print("mapped %s -> %s" % (a.owner, a.gh_user))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Copy the shared sponsor text in snippets/ into the READMEs (and other files) listed in sync.json, so it only ever needs
changing in one place.

A file says where a snippet goes with a pair of markers:

    <!-- sponsors:short -->
    (replaced with snippets/short.md)
    <!-- /sponsors:short -->

A snippet can include another one with {{name}}. Files without any markers are left alone.

Usage:  sync-readmes.py [--dry-run]
        sync-readmes.py --local     only update this repo's own files, on disk

Uses the gh command, so it needs a GitHub login (or GH_TOKEN) that can write to the repos in sync.json.
"""

import base64
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"(<!-- sponsors:([a-z0-9-]+) -->).*?(<!-- /sponsors:\2 -->)", re.DOTALL)
INCLUDE = re.compile(r"\{\{([a-z0-9-]+)\}\}")


def load_snippets():
    snippets = {path.stem: path.read_text().strip() for path in (ROOT / "snippets").glob("*.md")}

    def expand(name, seen=()):
        if name in seen:
            sys.exit(f"Snippet {name} includes itself")
        if name not in snippets:
            sys.exit(f"Unknown snippet: {name}")
        return INCLUDE.sub(lambda m: expand(m.group(1), seen + (name,)), snippets[name])

    return {name: expand(name) for name in snippets}


def gh(*args, data=None):
    result = subprocess.run(["gh", "api", *args], input=data, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def fill(text, snippets, where):
    def replace(match):
        name = match.group(2)
        if name not in snippets:
            raise SystemExit(f"{where} uses an unknown snippet: {name}")
        return match.group(1) + "\n" + snippets[name] + "\n" + match.group(3)

    return BLOCK.sub(replace, text)


def sync(repo, branch, path, snippets, dry_run):
    where = f"{repo} {branch} {path}"
    try:
        current = gh(f"repos/{repo}/contents/{path}?ref={branch}")
    except RuntimeError as error:
        print(f"!! {where}: couldn't read it ({error})")
        return False
    old = base64.b64decode(current["content"]).decode()
    new = fill(old, snippets, where)
    if new == old:
        print(f"   {where}: up to date")
        return True

    if dry_run:
        print(f"-- {where}: would change")
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), path, path))
        return True

    body = json.dumps({
        "message": "Update sponsor text\n\nCopied from https://github.com/DigiNode-Tools/diginode-sponsors/tree/main/snippets",
        "content": base64.b64encode(new.encode()).decode(),
        "sha": current["sha"],
        "branch": branch,
    })
    try:
        gh("-X", "PUT", f"repos/{repo}/contents/{path}", "--input", "-", data=body)
    except RuntimeError as error:
        print(f"!! {where}: couldn't update it ({error})")
        return False
    print(f"++ {where}: updated")
    return True


def main():
    dry_run = "--dry-run" in sys.argv[1:]
    snippets = load_snippets()
    targets = json.loads((ROOT / "sync.json").read_text())["files"]

    if "--local" in sys.argv[1:]:
        for target in targets:
            if target["repo"] == "DigiNode-Tools/diginode-sponsors":
                file = ROOT / target["path"]
                file.write_text(fill(file.read_text(), snippets, target["path"]))
                print(f"   {target['path']}: filled in")
        return

    ok = True
    for target in targets:
        for branch in target["branches"]:
            ok &= sync(target["repo"], branch, target["path"], snippets, dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

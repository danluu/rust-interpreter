#!/usr/bin/env python3
"""Create task-owned, pinned source snapshots without modifying original checkouts."""
import argparse
import json
import subprocess
from pathlib import Path
from workflow_projects import WORKFLOW_ONLY_PROJECTS

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "fre": "https://github.com/danluu/fre.git",
    "rg-aot": None,
    "pgrust": "https://github.com/malisper/pgrust.git",
    "ruff": "https://github.com/astral-sh/ruff.git",
    "nushell": "https://github.com/nushell/nushell.git",
    "cg-clif": "https://github.com/rust-lang/rustc_codegen_cranelift.git",
    "cargo": "https://github.com/rust-lang/cargo.git",
}
CONFIG = json.loads((ROOT / "benchmarks/corpus.json").read_text())
PINS = {name: value["revision"] for name, value in CONFIG["projects"].items()}
PINS["cg-clif"] = "db693f7dbcfab9af2a89b703096f692417e2f756"
PINS["cargo"] = "3c0b534756e166d12eb9fd2e1abfe5b42ac6101e"
SOURCES.update({name: project['source'] for name, project in WORKFLOW_ONLY_PROJECTS.items()})
PINS.update({name: project['revision'] for name, project in WORKFLOW_ONLY_PROJECTS.items()})


def run(args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def prepare(name, override=None):
    dest = ROOT / ".work" / "sources" / name
    marker = dest / ".rust-interp-owned.json"
    if dest.exists():
        if not marker.exists():
            raise RuntimeError("Refusing to reuse unmarked directory: " + str(dest))
        data = json.loads(marker.read_text())
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
        if data.get("owner") != str(ROOT) or data.get("revision") != PINS[name] or revision != PINS[name]:
            raise RuntimeError("Incomplete or mismatched snapshot: " + str(dest))
        print(name + ": verified " + revision, flush=True)
        return
    source = override or SOURCES[name]
    sibling = ROOT.parent / name
    if override is None and name in ["fre", "rg-aot"] and (sibling / ".git").exists():
        source = sibling.as_uri()
    if source is None:
        raise RuntimeError("Provide --source rg-aot=PATH_OR_GIT_URL for the private repository")
    if Path(source).is_dir():
        source = Path(source).resolve().as_uri()
    dest.mkdir(parents=True)
    marker.write_text(json.dumps({"owner": str(ROOT), "source": source}))
    run(["git", "init", "--quiet"], dest)
    run(["git", "-c", "gc.auto=0", "fetch", "--depth=1", source, PINS[name]], dest)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], dest)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
    if revision != PINS[name]:
        raise RuntimeError("Fetched revision mismatch")
    marker.write_text(json.dumps({"owner": str(ROOT), "source": source, "revision": revision}, indent=2) + "\n")
    print(name + ": " + revision, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="+", choices=list(SOURCES))
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH_OR_GIT_URL")
    args = parser.parse_args()
    overrides = dict(item.split("=", 1) for item in args.source)
    for project in args.projects:
        prepare(project, overrides.get(project))

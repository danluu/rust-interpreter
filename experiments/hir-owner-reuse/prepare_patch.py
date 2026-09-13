#!/usr/bin/env python3
"""Generate a source-only patch; never write to the supplied compiler checkout."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

BASE = "58e1e1f5311f4424ea81def4763081f6da62d9b3"
ROOT = Path(__file__).resolve().parent


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected one source anchor: {old[:100]!r}")
    return text.replace(old, new, 1)


def changes(originals: dict[str, str]) -> dict[str, str]:
    result = dict(originals)
    path = "compiler/rustc_ast_lowering/src/lib.rs"
    result[path] = replace_once(result[path], "mod item;\n", "mod item;\nmod owner_cache;\n")
    path = "compiler/rustc_ast_lowering/src/item.rs"
    value = result[path]
    value = replace_once(value, "        owner: NodeId,\n        f: impl FnOnce", "        owner: NodeId,\n        cache_input: Option<&Item>,\n        f: impl FnOnce")
    value = replace_once(value,
        "        let mut lctx = LoweringContext::new(self.tcx, self.resolver, owner);\n\n        let item = f(&mut lctx);",
        "        let candidate = cache_input.and_then(|item| crate::owner_cache::prepare(self.tcx, self.resolver, item));\n"
        "        let mut lctx = LoweringContext::new(self.tcx, self.resolver, owner);\n\n"
        "        let item = match candidate.as_ref().and_then(|candidate| crate::owner_cache::restore(candidate, &mut lctx)) {\n"
        "            Some(item) => item,\n            None => f(&mut lctx),\n        };\n"
        "        if let Some(candidate) = &candidate { crate::owner_cache::save(candidate, &lctx, item); }")
    value = replace_once(value, "self.with_lctx(CRATE_NODE_ID, |", "self.with_lctx(CRATE_NODE_ID, None, |")
    value = replace_once(value, "self.with_lctx(item.id, |lctx| hir::OwnerNode::Item", "self.with_lctx(item.id, Some(item), |lctx| hir::OwnerNode::Item")
    for kind in ("TraitItem", "ImplItem", "ForeignItem"):
        value = replace_once(value, f"self.with_lctx(item.id, |lctx| hir::OwnerNode::{kind}", f"self.with_lctx(item.id, None, |lctx| hir::OwnerNode::{kind}")
    result[path] = value
    path = "compiler/rustc_ast_lowering/Cargo.toml"
    value = replace_once(result[path], 'rustc_session = { path = "../rustc_session" }', 'rustc_serialize = { path = "../rustc_serialize" }\nrustc_session = { path = "../rustc_session" }')
    result[path] = replace_once(value, 'smallvec = { version = "1.8.1", features = ["union", "may_dangle"] }',
        'serde = { version = "1.0.219", features = ["derive"] }\nserde_json = "1.0.59"\nsmallvec = { version = "1.8.1", features = ["union", "may_dangle"] }')
    path = "Cargo.lock"
    start = result[path].index('name = "rustc_ast_lowering"\n')
    end = result[path].index("\n[[package]]", start)
    block = result[path][start:end]
    updated = replace_once(block, ' "rustc_session",\n', ' "rustc_serialize",\n "rustc_session",\n')
    updated = replace_once(updated, ' "smallvec",\n', ' "serde",\n "serde_json",\n "smallvec",\n')
    result[path] = result[path][:start] + updated + result[path][end:]
    path = "compiler/rustc_session/src/options.rs"
    result[path] = replace_once(result[path], '    #[rustc_lint_opt_deny_field_access("use `Session::sanitizers()` instead of this field")]\n',
        '    reuse_hir_owners: bool = (false, parse_bool, [TRACKED],\n'
        '        "reuse conservative resolved scalar HIR owners (default: no)"),\n'
        '    #[rustc_lint_opt_deny_field_access("use `Session::sanitizers()` instead of this field")]\n')
    path = "compiler/rustc_interface/src/tests.rs"
    result[path] = replace_once(result[path], '    tracked!(sanitizer, SanitizerSet::ADDRESS);',
        '    tracked!(reuse_hir_owners, true);\n    tracked!(sanitizer, SanitizerSet::ADDRESS);')
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True).stdout.strip()
    if revision != BASE:
        raise ValueError("compiler checkout must remain at the exact reviewed base")
    originals = {}
    for name in ("Cargo.lock", "compiler/rustc_ast_lowering/Cargo.toml", "compiler/rustc_ast_lowering/src/lib.rs",
                 "compiler/rustc_ast_lowering/src/item.rs", "compiler/rustc_session/src/options.rs", "compiler/rustc_interface/src/tests.rs"):
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"non-regular compiler input: {name}")
        data = path.read_bytes()
        committed = subprocess.run(["git", "show", f"{BASE}:{name}"], cwd=source, check=True, capture_output=True).stdout
        if data != committed:
            raise ValueError(f"compiler input differs from base: {name}")
        originals[name] = data.decode()
    updated = changes(originals)
    inputs = {}
    for path in sorted((ROOT / "candidate" / "owner_cache").glob("*.rs")):
        name = f"compiler/rustc_ast_lowering/src/owner_cache/{path.name}"
        if (source / name).exists():
            raise ValueError(f"proposed new compiler source already exists: {name}")
        updated[name] = path.read_text()
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    updated["tests/run-make/reuse-hir-owners/rmake.rs"] = (ROOT / "candidate/rmake.rs").read_text()
    inputs["candidate/rmake.rs"] = hashlib.sha256((ROOT / "candidate/rmake.rs").read_bytes()).hexdigest()
    pieces = []
    files = {}
    for name, after in sorted(updated.items()):
        before = originals.get(name, "")
        pieces.append(f"diff --git a/{name} b/{name}\n")
        if name not in originals:
            pieces.append("new file mode 100644\n")
        pieces.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{name}" if name in originals else "/dev/null", tofile=f"b/{name}"))
        files[name] = {"before_sha256": hashlib.sha256(before.encode()).hexdigest() if name in originals else None,
                       "after_sha256": hashlib.sha256(after.encode()).hexdigest()}
    patch = "".join(pieces).encode()
    (ROOT / "reuse-hir-owners.patch").write_bytes(patch)
    manifest = {"status": "source-only-uncompiled-unrun", "base_commit": BASE,
                "patch_sha256": hashlib.sha256(patch).hexdigest(), "patch_bytes": len(patch), "files": files,
                "candidate_inputs": inputs, "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "compiler_checkout_modified": False, "builds_or_tests_run": False}
    (ROOT / "patch.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": manifest["status"], "files": len(files), "patch_bytes": len(patch), "patch_sha256": manifest["patch_sha256"]}))


if __name__ == "__main__":
    main()

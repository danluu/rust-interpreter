#!/usr/bin/env python3
"""Produce an unapplied experiment patch from the frozen compiler sources."""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess


BASE = "73a11f167216d3955c277ed47f9b8cc68208105b"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"expected one occurrence: {old[:100]!r}")
    return text.replace(old, new, 1)


def partitioning(text):
    text = replace_once(
        text,
        "use rustc_data_structures::stable_hash::StableHasher;",
        "use rustc_data_structures::stable_hash::{StableHasher, ToStableHashKey};",
    )
    text = replace_once(
        text,
        "fn partition<'tcx, I>(\n    tcx: TyCtxt<'tcx>,\n    mono_items: I,\n    usage_map: &UsageMap<'tcx>,\n) -> Vec<CodegenUnit<'tcx>>\nwhere\n    I: Iterator<Item = MonoItem<'tcx>>,\n{",
        "fn partition<'tcx>(\n    tcx: TyCtxt<'tcx>,\n    mono_items: &[MonoItem<'tcx>],\n    usage_map: &UsageMap<'tcx>,\n) -> Vec<CodegenUnit<'tcx>> {",
    )
    text = replace_once(
        text,
        "    let cx = &PartitioningCx { tcx, usage_map };\n",
        "    let cx = &PartitioningCx { tcx, usage_map };\n"
        "    let stable_mono_buckets = use_stable_mono_buckets(tcx, mono_items);\n",
    )
    text = replace_once(
        text,
        "        let placed = place_mono_items(cx, mono_items);",
        "        let placed = place_mono_items(cx, mono_items.iter().copied(), stable_mono_buckets);",
    )
    text = replace_once(
        text,
        "    // Merge until we don't exceed the max CGU count.\n"
        "    // `merge_codegen_units` is responsible for updating the CGU size\n"
        "    // estimates.\n    {",
        "    // Merge until we don't exceed the max CGU count.\n"
        "    // `merge_codegen_units` is responsible for updating the CGU size\n"
        "    // estimates.\n    if !stable_mono_buckets {",
    )
    text = replace_once(
        text,
        "fn place_mono_items<'tcx, I>(cx: &PartitioningCx<'_, 'tcx>, mono_items: I) -> PlacedMonoItems<'tcx>\nwhere",
        """fn use_stable_mono_buckets<'tcx>(tcx: TyCtxt<'tcx>, mono_items: &[MonoItem<'tcx>]) -> bool {
    if !tcx.sess.opts.unstable_opts.stable_mono_cgu_partitioning
        || tcx.sess.opts.incremental.is_none()
        || tcx.sess.instrument_coverage()
    {
        return false;
    }

    let mut roots = 0;
    for item in mono_items {
        if item.explicit_linkage(tcx).is_some() {
            return false;
        }
        match item {
            MonoItem::GlobalAsm(..) => return false,
            MonoItem::Fn(instance)
                if tcx
                    .codegen_instance_attrs(instance.def)
                    .flags
                    .contains(CodegenFnAttrFlags::NAKED) =>
            {
                return false;
            }
            _ => {}
        }
        if matches!(item.instantiation_mode(tcx), InstantiationMode::GloballyShared { .. }) {
            roots += 1;
        }
    }
    roots > tcx.sess.codegen_units().as_usize()
}

fn place_mono_items<'tcx, I>(
    cx: &PartitioningCx<'_, 'tcx>,
    mono_items: I,
    stable_mono_buckets: bool,
) -> PlacedMonoItems<'tcx>
where""",
    )
    text = replace_once(
        text,
        "    let cgu_name_cache = &mut UnordMap::default();\n\n    for mono_item in mono_items {",
        """    let cgu_name_cache = &mut UnordMap::default();
    let bucket_names: Vec<_> = if stable_mono_buckets {
        let count = cx.tcx.sess.codegen_units().as_usize();
        (0..count)
            .map(|index| {
                let name = cgu_name_builder.build_cgu_name(
                    LOCAL_CRATE,
                    ["stable-mono-cgu-v1"],
                    Some(format!("{count}-{index}")),
                );
                let mut cgu = CodegenUnit::new(name);
                cgu.set_symbol_name(Symbol::intern(&rustc_symbol_mangling::mangle_cgu(
                    cx.tcx,
                    LOCAL_CRATE,
                    Either::Right(cgu.name().as_str()),
                )));
                assert!(codegen_units.insert(name, cgu).is_none());
                name
            })
            .collect()
    } else {
        Vec::new()
    };

    for mono_item in mono_items {""",
    )
    text = replace_once(
        text,
        """        let characteristic_def_id = characteristic_def_id_of_mono_item(cx.tcx, mono_item);
        let is_volatile = is_incremental_build && mono_item.is_generic_fn();

        let cgu_name = match characteristic_def_id {
            Some(def_id) => compute_codegen_unit_name(
                cx.tcx,
                cgu_name_builder,
                def_id,
                is_volatile,
                cgu_name_cache,
            ),
            None => fallback_cgu_name(cgu_name_builder),
        };""",
        """        let cgu_name = if stable_mono_buckets {
            let hash = cx
                .tcx
                .with_stable_hashing_context(|mut hcx| mono_item.to_stable_hash_key(&mut hcx));
            let index = (hash.to_smaller_hash().as_u64() % bucket_names.len() as u64) as usize;
            bucket_names[index]
        } else {
            let characteristic_def_id = characteristic_def_id_of_mono_item(cx.tcx, mono_item);
            let is_volatile = is_incremental_build && mono_item.is_generic_fn();

            match characteristic_def_id {
                Some(def_id) => compute_codegen_unit_name(
                    cx.tcx,
                    cgu_name_builder,
                    def_id,
                    is_volatile,
                    cgu_name_cache,
                ),
                None => fallback_cgu_name(cgu_name_builder),
            }
        };""",
    )
    return replace_once(
        text,
        "partition(tcx, items.iter().copied(), &usage_map)",
        "partition(tcx, &items, &usage_map)",
    )


def options(text):
    return replace_once(
        text,
        '    #[rustc_lint_opt_deny_field_access("use `Session::stack_protector` instead of this field")]\n',
        '    stable_mono_cgu_partitioning: bool = (false, parse_bool, [TRACKED],\n'
        '        "place incremental mono items into stable hash buckets (default: no)"),\n'
        '    #[rustc_lint_opt_deny_field_access("use `Session::stack_protector` instead of this field")]\n',
    )


def config(text):
    return replace_once(
        text,
        "    let mut unstable_opts = UnstableOptions::build(early_dcx, matches, &mut collected_options);\n",
        """    let mut unstable_opts = UnstableOptions::build(early_dcx, matches, &mut collected_options);

    if unstable_opts.stable_cgu_partitioning && unstable_opts.stable_mono_cgu_partitioning {
        early_dcx.early_fatal(
            "-Zstable-cgu-partitioning and -Zstable-mono-cgu-partitioning cannot be enabled together",
        );
    }
""",
    )


def option_test(text):
    return replace_once(
        text,
        "    tracked!(stable_cgu_partitioning, true);\n",
        "    tracked!(stable_cgu_partitioning, true);\n    tracked!(stable_mono_cgu_partitioning, true);\n",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("compiler", type=Path)
    args = parser.parse_args()
    compiler = args.compiler.resolve()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=compiler, text=True).strip()
    if actual != BASE:
        raise ValueError(f"expected frozen compiler {BASE}, got {actual}")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=compiler):
        raise ValueError("tracked compiler source must be clean")
    here = Path(__file__).resolve().parent
    edits = {
        "compiler/rustc_monomorphize/src/partitioning.rs": partitioning,
        "compiler/rustc_session/src/options.rs": options,
        "compiler/rustc_session/src/config.rs": config,
        "compiler/rustc_interface/src/tests.rs": option_test,
    }
    inventory = []
    chunks = []
    for path, transform in edits.items():
        old = (compiler / path).read_text()
        new = transform(old)
        chunks.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{path}", f"b/{path}"))
        inventory.append({"path": path, "base_sha256": hashlib.sha256(old.encode()).hexdigest(), "patched_sha256": hashlib.sha256(new.encode()).hexdigest()})
    for source, path in [
        ("rmake.rs", "tests/run-make/stable-mono-cgu-partitioning/rmake.rs"),
        ("stable-mono-merging.rs", "tests/codegen-units/partitioning/stable-mono-merging.rs"),
    ]:
        if (compiler / path).exists():
            raise ValueError(f"new test path already exists: {path}")
        new = (here / "tests" / source).read_text()
        chunks.extend(difflib.unified_diff([], new.splitlines(True), "/dev/null", f"b/{path}"))
        inventory.append({"path": path, "base_sha256": None, "patched_sha256": hashlib.sha256(new.encode()).hexdigest()})
    patch = "".join(chunks).encode()
    (here / "rustc.patch").write_bytes(patch)
    (here / "source-identity.json").write_text(json.dumps({
        "schema": 1, "base_commit": BASE, "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "status": "source-only; not compiled, formatted, tested, or benchmarked",
        "files": inventory,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()

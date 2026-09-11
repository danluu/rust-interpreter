#!/usr/bin/env python3
"""Apply a fail-closed patch to our pinned, task-owned cg_clif snapshot."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".work/sources/cg-clif"
PIN = "db693f7dbcfab9af2a89b703096f692417e2f756"


def patch():
    marker = json.loads((SOURCE / ".rust-interp-owned.json").read_text())
    assert marker["owner"] == str(ROOT) and marker["revision"] == PIN
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip() == PIN
    changes = {
        "Cargo.toml": [
            ('"all-native-arch"]', '"all-native-arch", "incremental-cache"]'),
            ('[dependencies]\n', '[dependencies]\nrust-interp-function-cache = { path = "../../../crates/function-cache" }\n'),
        ],
        "src/lib.rs": [
            ('mod cast;\n', 'mod cast;\nmod cache_adapter;\n'),
            ('    flags_builder.set("regalloc_checker", enable_verifier).unwrap();',
             '    flags_builder.set("regalloc_checker", enable_verifier).unwrap();\n'
             '    if std::env::var_os("RUST_INTERP_CACHE_VERIFY").is_some() {\n'
             '        flags_builder.set("enable_incremental_compilation_cache_checks", "true").unwrap();\n    }'),
        ],
        "src/driver/aot.rs": [
            ('let module = UnwindModule::new(ObjectModule::new(builder), true);',
             'let mut module = UnwindModule::new(ObjectModule::new(builder), true);\n'
             '    module.function_cache = crate::cache_adapter::FunctionCache::from_env();'),
        ],
        "src/unwind_module.rs": [
            ('    unwind_context: UnwindContext,', '    unwind_context: UnwindContext,\n    pub(crate) function_cache: Option<crate::cache_adapter::FunctionCache>,'),
            ('UnwindModule { module, unwind_context }', 'UnwindModule { module, unwind_context, function_cache: None }'),
             ('        self.module.define_function_with_control_plane(func, ctx, ctrl_plane)?;', '''        if let Some(cache) = self.function_cache.as_mut().filter(|_| !ctx.want_disasm) {
            let (_, hit) = ctx.compile_with_cache(self.module.isa(), cache, ctrl_plane)?;
            if hit { cache.hits += 1; } else { cache.misses += 1; }
            let compiled = ctx.compiled_code().unwrap();
            let relocs = compiled.buffer.relocs().iter()
                .map(|r| ModuleReloc::from_mach_reloc(r, &ctx.func, func))
                .collect::<Vec<_>>();
            self.module.define_function_bytes(func, compiled.buffer.alignment as u64,
                compiled.buffer.data(), &relocs)?;
        } else {
            self.module.define_function_with_control_plane(func, ctx, ctrl_plane)?;
        }'''),
        ],
    }
    # Validate every preimage before changing any file. Re-applying our exact
    # patch is allowed; unrelated modifications cause failure.
    writes = {}
    for name, replacements in changes.items():
        original = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=SOURCE, text=True)
        patched = original
        for before, after in replacements:
            assert patched.count(before) == 1, (name, before)
            patched = patched.replace(before, after)
        assert (SOURCE / name).read_text() in [original, patched], "Unexpected modification: " + name
        writes[name] = patched
    for name, content in writes.items():
        if (SOURCE / name).read_text() != content:
            (SOURCE / name).write_text(content)
    for destination, source in [("src/cache_adapter.rs", "compiler/cache_adapter.rs"), ("Cargo.lock", "compiler/Cargo.lock")]:
        content = (ROOT / source).read_bytes()
        path = SOURCE / destination
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
    print("Applied function cache to cg_clif " + PIN)


if __name__ == "__main__":
    patch()

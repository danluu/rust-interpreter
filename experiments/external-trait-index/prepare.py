#!/usr/bin/env python3
"""Produce an unapplied compiler patch from a pinned, read-only source tree."""
import argparse
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

BASE = '58e1e1f5311f4424ea81def4763081f6da62d9b3'
HERE = Path(__file__).resolve().parent


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'expected exactly one source anchor: {old[:90]!r}')
    return source.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('compiler_source', type=Path)
    args = parser.parse_args()
    root = args.compiler_source.resolve()
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if head != BASE:
        raise ValueError('compiler revision differs from the reviewed base')
    sources = {}
    for name in ['compiler/rustc_resolve/src/lib.rs', 'compiler/rustc_session/src/options.rs',
                 'compiler/rustc_interface/src/tests.rs']:
        data = (root / name).read_bytes()
        committed = subprocess.check_output(['git', '-C', str(root), 'show', f'{BASE}:{name}'])
        if data != committed:
            raise ValueError(f'compiler input differs from committed source: {name}')
        sources[name] = data.decode()

    name = 'compiler/rustc_resolve/src/lib.rs'
    original = sources[name]
    candidate = replace_once(original,
        "    Extern(OnceLock<ResolutionTable<'ra>>),",
        """    Extern {
        table: OnceLock<ResolutionTable<'ra>>,
        // External binding keys never change after table publication. Cache only
        // the projection used by trait_may_have_item, not trait candidates or imports.
        assoc_item_names: OnceLock<FxHashSet<(Symbol, Namespace)>>,
    },""")
    candidate = replace_once(candidate,
        '            Resolutions::Extern(Default::default())',
        '            Resolutions::Extern { table: OnceLock::new(), assoc_item_names: OnceLock::new() }')
    candidate = replace_once(candidate,
        """            (Some(trait_module), Some((name, ns))) => self
                .resolutions(trait_module)
                .iter()
                .any(|(key, _name_resolution)| key.ns == ns && key.ident.name == name),""",
        """            (Some(trait_module), Some((name, ns))) => {
                // Populate through the ordinary path first, preserving metadata
                // loading and all reduced-graph construction side effects.
                let resolutions = self.resolutions(trait_module);
                if self.tcx.sess.opts.unstable_opts.index_external_trait_items
                    && let Resolutions::Extern { assoc_item_names, .. } =
                        &trait_module.0.0.lazy_resolutions
                {
                    // The original predicate intentionally ignores hygiene and
                    // disambiguators. Preserve that exact conservative projection,
                    // including keys without a current best declaration.
                    assoc_item_names
                        .get_or_init(|| resolutions.keys().map(|key| (key.ident.name, key.ns)).collect())
                        .contains(&(name, ns))
                } else {
                    // Local modules can gain bindings during expansion/import
                    // resolution. Never memoize their membership or a miss.
                    resolutions.iter().any(|(key, _)| key.ns == ns && key.ident.name == name)
                }
            },""")
    candidate = replace_once(candidate,
        '            Resolutions::Extern(extern_res) => {',
        '            Resolutions::Extern { table, .. } => {')
    candidate = replace_once(candidate,
        '                    extern_res\n                        .get_or_init',
        '                    table\n                        .get_or_init')
    candidate = replace_once(candidate,
        '            Resolutions::Extern(_) => {',
        '            Resolutions::Extern { .. } => {')
    updated = {name: candidate}
    name = 'compiler/rustc_session/src/options.rs'
    updated[name] = replace_once(sources[name],
        '    indirect_branch_cs_prefix: bool =',
        '    index_external_trait_items: bool = (false, parse_bool, [TRACKED],\n'
        '        "index immutable external trait item names during resolution (default: no)"),\n'
        '    indirect_branch_cs_prefix: bool =')

    name = 'compiler/rustc_interface/src/tests.rs'
    updated[name] = replace_once(sources[name],
        '    tracked!(incremental_ignore_spans, true);',
        '    tracked!(incremental_ignore_spans, true);\n'
        '    tracked!(index_external_trait_items, true);')

    patch = ''.join(''.join(difflib.unified_diff(sources[name].splitlines(keepends=True),
                    data.splitlines(keepends=True), fromfile='a/' + name, tofile='b/' + name))
                    for name, data in updated.items())
    output = HERE / 'index-external-trait-items.patch'
    output.write_text(patch)
    manifest = {'schema_version': 1, 'base': BASE, 'applied': False, 'compiled': False,
        'benchmarked': False, 'policy': 'external-trait-item-name-index-v1',
        'flag': '-Zindex-external-trait-items=yes', 'default': False,
        'option_tracking': 'TRACKED',
        'patch_sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'files': {}}
    for name, data in updated.items():
        path = HERE / 'candidate' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        manifest['files'][name] = {
            'base_sha256': hashlib.sha256(sources[name].encode()).hexdigest(),
            'candidate_sha256': hashlib.sha256(data.encode()).hexdigest()}
    subprocess.run(['git', '-C', str(root), 'apply', '--check', str(output)], check=True)
    for name, data in sources.items():
        if (root / name).read_bytes() != data.encode():
            raise ValueError('read-only compiler source changed during preparation')
    (HERE / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()

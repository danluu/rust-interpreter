#!/usr/bin/env python3
"""Generate the capture-only compiler patch; never modify its source checkout."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

BASE = '58e1e1f5311f4424ea81def4763081f6da62d9b3'
GATE_SHA = '6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1'
ROOT = Path(__file__).resolve().parent
FILES = ['Cargo.lock', 'compiler/rustc_ast_lowering/Cargo.toml',
         'compiler/rustc_ast_lowering/src/lib.rs', 'compiler/rustc_ast_lowering/src/item.rs',
         'compiler/rustc_ast_lowering/src/pat.rs', 'compiler/rustc_ast_lowering/src/expr.rs',
         'compiler/rustc_hir_id/src/definitions.rs', 'compiler/rustc_session/src/options.rs',
         'compiler/rustc_interface/src/tests.rs']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('expected exactly one pinned source anchor: ' + repr(old[:100]))
    return text.replace(old, new, 1)


def changes(original):
    result = dict(original)
    path = 'compiler/rustc_ast_lowering/src/lib.rs'
    value = replace(result[path], 'mod block;\n', 'mod block;\nmod body_cache;\n')
    value = replace(value, '    attribute_parser: AttributeParser<\'hir>,\n',
        '    attribute_parser: AttributeParser<\'hir>,\n'
        '    body_candidate: Option<body_cache::Candidate>,\n'
        '    body_trace: Option<body_cache::Trace>,\n')
    value = replace(value, '            move_expr_bindings: Vec::new(),\n',
        '            move_expr_bindings: Vec::new(),\n            body_candidate: None,\n            body_trace: None,\n')
    value = replace(value, '    impl ReloweringChecker {\n',
        '    impl ReloweringChecker {\n'
        '        pub(crate) fn body_snapshot(&self) -> Option<NodeMap<hir::ItemLocalId>> {\n'
        '            (!self.can_relower).then(|| self.node_id_to_local_id.clone())\n        }\n\n')
    value = replace(value, '    ) -> LocalDefId {\n        let parent = self.curr_owner.owner_id.def_id;\n',
        '    ) -> LocalDefId {\n        self.reject_body_capture("create-def");\n'
        '        let parent = self.curr_owner.owner_id.def_id;\n')
    value = replace(value, '    fn next_node_id(&mut self) -> NodeId {\n',
        '    fn next_node_id(&mut self) -> NodeId {\n        self.reject_body_capture("new-ast-node");\n')
    value = replace(value, '        let child_owner = PerOwnerLoweringState::new(self.resolver, owner);\n',
        '        self.reject_body_capture("nested-owner");\n'
        '        let child_owner = PerOwnerLoweringState::new(self.resolver, owner);\n')
    value = replace(value, '        hir_id\n    }\n\n    /// Generate a new `HirId` without a backing `NodeId`.\n',
        '        if let Some(trace) = &mut self.body_trace { trace.ast(ast_node_id, local_id); }\n'
        '        hir_id\n    }\n\n    /// Generate a new `HirId` without a backing `NodeId`.\n')
    value = replace(value, '        HirId { owner, local_id }\n    }\n\n    #[instrument(level = "trace", skip(self))]\n    fn lower_res',
        '        if let Some(trace) = &mut self.body_trace { trace.synthetic(local_id); }\n'
        '        HirId { owner, local_id }\n    }\n\n    #[instrument(level = "trace", skip(self))]\n    fn lower_res')
    value = replace(value, '    ) -> Vec<hir::Attribute> {\n        let l = self.span_lowerer();\n',
        '    ) -> Vec<hir::Attribute> {\n        self.reject_body_capture("attribute-parser");\n'
        '        let l = self.span_lowerer();\n')
    result[path] = value

    path = 'compiler/rustc_ast_lowering/src/item.rs'
    value = replace(result[path], '    fn lower_item(&mut self, i: &Item) -> &\'hir hir::Item<\'hir> {\n',
        '    fn lower_item(&mut self, i: &Item) -> &\'hir hir::Item<\'hir> {\n'
        '        if let ItemKind::Fn(function) = &i.kind {\n'
        '            self.body_candidate = crate::body_cache::prepare(self.tcx, self.resolver,\n'
        '                i.id, i.span, function, "free-function");\n        }\n')
    value = replace(value, '    fn lower_trait_item(&mut self, i: &AssocItem) -> &\'hir hir::TraitItem<\'hir> {\n',
        '    fn lower_trait_item(&mut self, i: &AssocItem) -> &\'hir hir::TraitItem<\'hir> {\n'
        '        if let AssocItemKind::Fn(function) = &i.kind {\n'
        '            self.body_candidate = crate::body_cache::prepare(self.tcx, self.resolver,\n'
        '                i.id, i.span, function, "provided-trait-method");\n        }\n')
    value = replace(value, '            matches!(self.tcx.def_kind(parent_id), DefKind::Impl { of_trait: true });\n',
        '            matches!(self.tcx.def_kind(parent_id), DefKind::Impl { of_trait: true });\n'
        '        if let AssocItemKind::Fn(function) = &i.kind {\n'
        '            self.body_candidate = crate::body_cache::prepare(self.tcx, self.resolver,\n'
        '                i.id, i.span, function, if is_in_trait_impl { "trait-impl-method" }\n'
        '                else { "inherent-impl-method" });\n        }\n')
    value = replace(value, '        self.lower_fn_body(decl, contract, |this| this.lower_block_expr(body))\n',
        '        self.lower_fn_body(decl, contract, |this| crate::body_cache::lower(this, body))\n')
    result[path] = value
    path = 'compiler/rustc_ast_lowering/src/pat.rs'
    value = replace(result[path], 'self.curr_owner.ident_and_label_to_local_id.insert(id, hir_id.local_id);',
        'self.insert_body_binding(id, hir_id.local_id);')
    result[path] = replace(value, 'self.curr_owner.ident_and_label_to_local_id.insert(p.id, hir_id.local_id);',
        'self.insert_body_binding(p.id, hir_id.local_id);')
    path = 'compiler/rustc_ast_lowering/src/expr.rs'
    result[path] = replace(result[path], 'self.curr_owner.ident_and_label_to_local_id.insert(dest_id, dest_hir_id.local_id);',
        'self.insert_body_binding(dest_id, dest_hir_id.local_id);')

    path = 'compiler/rustc_hir_id/src/definitions.rs'
    result[path] = replace(result[path], '#[derive(Debug, Default, Clone)]\npub struct PerParentDisambiguatorState',
        '#[derive(Debug, Default, Clone, PartialEq, Eq)]\npub struct PerParentDisambiguatorState')
    path = 'compiler/rustc_ast_lowering/Cargo.toml'
    value = replace(result[path], 'rustc_session = { path = "../rustc_session" }',
        'rustc_serialize = { path = "../rustc_serialize" }\nrustc_session = { path = "../rustc_session" }')
    result[path] = replace(value, 'smallvec = { version = "1.8.1", features = ["union", "may_dangle"] }',
        'serde = { version = "1.0.219", features = ["derive"] }\nserde_json = "1.0.59"\n'
        'smallvec = { version = "1.8.1", features = ["union", "may_dangle"] }')
    path = 'Cargo.lock'
    start = result[path].index('name = "rustc_ast_lowering"\n')
    end = result[path].index('\n[[package]]', start)
    block = replace(result[path][start:end], ' "rustc_session",\n', ' "rustc_serialize",\n "rustc_session",\n')
    block = replace(block, ' "smallvec",\n', ' "serde",\n "serde_json",\n "smallvec",\n')
    result[path] = result[path][:start] + block + result[path][end:]
    path = 'compiler/rustc_session/src/options.rs'
    result[path] = replace(result[path], '    #[rustc_lint_opt_deny_field_access("use `Session::sanitizers()` instead of this field")]\n',
        '    hir_body_cache_capture: bool = (false, parse_bool, [TRACKED],\n'
        '        "capture conservative HIR body journals without reusing HIR (default: no)"),\n'
        '    #[rustc_lint_opt_deny_field_access("use `Session::sanitizers()` instead of this field")]\n')
    path = 'compiler/rustc_interface/src/tests.rs'
    result[path] = replace(result[path], '    tracked!(sanitizer, SanitizerSet::ADDRESS);',
        '    tracked!(hir_body_cache_capture, true);\n    tracked!(sanitizer, SanitizerSet::ADDRESS);')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=source, check=True, capture_output=True, text=True).stdout.strip()
    if revision != BASE:
        raise ValueError('pinned compiler source revision differs')
    original = {}
    for name in FILES:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('compiler input is not a regular file: ' + name)
        data = path.read_bytes()
        committed = subprocess.run(['git', 'show', BASE + ':' + name], cwd=source, check=True, capture_output=True).stdout
        if data != committed:
            raise ValueError('compiler source input changed: ' + name)
        original[name] = data.decode()
    updated = changes(original)
    gate_path = ROOT.parent / 'hir-body-reuse/gate.rs'
    gate = gate_path.read_bytes()
    if sha(gate) != GATE_SHA:
        raise ValueError('qualified gate changed')
    inputs = {str(gate_path.relative_to(ROOT.parent)): sha(gate)}
    for path in sorted((ROOT / 'candidate/body_cache').glob('*.rs')):
        updated['compiler/rustc_ast_lowering/src/body_cache/' + path.name] = path.read_text()
        inputs[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    adapter = ROOT / 'candidate/input_adapter.rs'
    inputs[str(adapter.relative_to(ROOT))] = sha(adapter.read_bytes())
    updated['compiler/rustc_ast_lowering/src/body_cache/input.rs'] = gate.decode() + adapter.read_text()
    for name in ['rmake.rs', 'fixture.rs']:
        path = ROOT / 'candidate' / name
        inputs[str(path.relative_to(ROOT))] = sha(path.read_bytes())
        updated['tests/run-make/hir-body-cache-capture/' + name] = path.read_text()
    # Acyclic source identity binds all actual hooks and the complete qualified
    # gate/validator/storage, including unchanged portions of patched files.
    identity = sha(json.dumps({name: sha(text.encode()) for name, text in sorted(updated.items())},
        sort_keys=True, separators=(',', ':')).encode())
    updated['compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'] = \
        'pub(super) const SOURCE_IDENTITY: &str = "' + identity + '";\n'
    pieces, files = [], {}
    for name, after in sorted(updated.items()):
        if name not in original and (source / name).exists():
            raise ValueError('new compiler output path already exists: ' + name)
        before = original.get(name, '')
        pieces.append(f'diff --git a/{name} b/{name}\n')
        if name not in original:
            pieces.append('new file mode 100644\n')
        pieces.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile='a/' + name if name in original else '/dev/null', tofile='b/' + name))
        files[name] = dict(before_sha256=sha(before.encode()) if name in original else None, after_sha256=sha(after.encode()))
    patch = ''.join(pieces).encode()
    (ROOT / 'capture-body-journals.patch').write_bytes(patch)
    manifest = dict(status='source-only-uncompiled-unrun-capture-boundary', base_commit=BASE,
        gate_sha256=GATE_SHA, candidate_inputs=inputs, generator_sha256=sha(Path(__file__).read_bytes()),
        files=files, source_identity=identity, patch_bytes=len(patch), patch_sha256=sha(patch),
        compiler_checkout_modified=False, builds_or_tests_run=False,
        typed_hir_body_codec=False, cached_body_materialization=False, actual_cache_hit_path=False)
    (ROOT / 'patch.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    print(json.dumps({name: manifest[name] for name in ['status', 'patch_bytes', 'patch_sha256', 'source_identity']}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prepare an unrun, timing-ineligible real-AST qualification compiler patch."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
COMPILER = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
ARTIFACT_COMMIT = 'e4e7ac4ece88181f36f3ad9222e22a9eeb4506ca'
ARTIFACT = 'experiments/hir-input-walk/source-01/'
BASE = '7efc0d9484da82cd327deb3b48616f8ec81eaf8d'
INPUT = 'compiler/rustc_ast_lowering/src/body_cache/input.rs'
BODY = 'compiler/rustc_ast_lowering/src/body_cache/mod.rs'
IDENTITY = 'compiler/rustc_ast_lowering/src/body_cache/source_identity.rs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-optional-locks', '-C', str(root), *args])


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    out = HERE/'source-01'
    assert not out.exists() and not out.is_symlink()
    artifact = lambda name: git(REPOSITORY, 'show', ARTIFACT_COMMIT+':'+ARTIFACT+name)
    inherited_bytes = artifact('manifest.json')
    inherited = json.loads(inherited_bytes)
    assert inherited['base_commit'] == BASE
    assert inherited['patch_sha256'] == '7724d95c1fae787066b40f313fc638693c1d9c603bf1d57c3c1ad5934ae2fa68'
    assert sha(artifact('candidate.patch')) == inherited['patch_sha256']
    before = {}
    for name, digest in inherited['acyclic_identity_files'].items():
        data = (artifact('candidate/'+name) if name in inherited['changed_files']
                else git(COMPILER, 'show', BASE+':'+name))
        assert sha(data) == digest
        before[name] = data
    before[IDENTITY] = artifact('candidate/'+IDENTITY)
    assert sha(before[IDENTITY]) == inherited['candidate_hashes'][IDENTITY]
    old_input = git(COMPILER, 'show', BASE+':'+INPUT)
    assert old_input == artifact('base/'+INPUT)
    old_text = old_input.decode()
    marker = 'pub(super) fn current_nodes'
    assert old_text.count(marker) == 1
    old_function = old_text[old_text.index(marker):]
    assert old_function.endswith('    Ok(w.ordered)\n}\n')
    assert 'qualified-walker-disagreement' in old_function

    source = before[INPUT].decode()
    source = replace_once(source,
        '    Ok(ProbedInput { probe: Probe{input:Input{owner:',
        '    let probed = ProbedInput { probe: Probe{input:Input{owner:')
    source = replace_once(source, '        ordered: w.ordered })\n}', '''        ordered: w.ordered };
    // QUALIFICATION ONLY: this distinct compiler is forbidden for timings.
    // There is no environment switch or option that disables these checks.
    // The exact previous function compares both actual normalized Input byte
    // streams before returning its independently collected node order.
    let repeated = current_nodes(tcx, resolver, owner, span, f, &probed.probe)
        .unwrap_or_else(|reason| panic!("HIR input-walk audit rejected repeated traversal: {reason}"));
    assert_eq!(&probed.ordered, &repeated, "HIR input-walk audit node ordering differs");
    // Existing info reporting controls observation only; the audit above is
    // unconditional, including compilations comparing raw JSON diagnostics.
    if tcx.sess.opts.unstable_opts.incremental_info {
        eprintln!("[hir-input-walk-audit] accepted owner={} nodes={} params={} body={} traits={} candidates={} externals={}",
            f.ident.name, probed.ordered.len(), probed.probe.parameter_nodes,
            probed.probe.body_nodes, probed.probe.trait_entries,
            probed.probe.trait_candidates, probed.probe.external_resolutions);
    }
    Ok(probed)
}''')
    source += '\n// Exact baseline function retained only in this audit compiler.\n'+old_function
    body = replace_once(before[BODY].decode(),
        '    let (probe, ast_nodes) = input::probe(tcx, resolver, owner, span, function, role).ok()?.into_parts();\n',
        '''    let probed = match input::probe(tcx, resolver, owner, span, function, role) {
        Ok(value) => value,
        Err(reason) => {
            if tcx.sess.opts.unstable_opts.incremental_info {
                eprintln!("[hir-input-walk-audit] rejected owner={} reason={reason}", function.ident.name);
            }
            return None;
        }
    };
    let (probe, ast_nodes) = probed.into_parts();
''')
    after = dict(before, **{INPUT: source.encode(), BODY: body.encode()})
    closure = {name: sha(data) for name,data in after.items() if name != IDENTITY}
    identity = sha(json.dumps(closure,sort_keys=True,separators=(',',':')).encode())
    after[IDENTITY] = f'pub(super) const SOURCE_IDENTITY: &str = "{identity}";\n'.encode()
    changed = sorted(name for name in before if before[name] != after[name])
    assert changed == sorted([INPUT,BODY,IDENTITY])
    patch = []
    for name in changed:
        write(out/'performance-candidate'/name,before[name])
        write(out/'audit-candidate'/name,after[name])
        patch.append(f'diff --git a/{name} b/{name}\n')
        patch.extend(difflib.unified_diff(before[name].decode().splitlines(keepends=True),
            after[name].decode().splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name,n=5))
    patch = ''.join(patch).encode()
    write(out/'audit.patch',patch)
    write(out/'performance-manifest.json',inherited_bytes)
    write(out/'old-current-nodes.rs',old_function.encode())
    fixtures = {}
    for name in ['fixture.rs','rmake.rs']:
        path = 'tests/run-make/hir-body-cache-capture/'+name
        data = git(COMPILER,'show',BASE+':'+path)
        dest = ('fixture.rs' if name == 'fixture.rs' else 'inherited-rmake.rs')
        write(out/'fixtures'/dest,data)
        fixtures[dest] = dict(sha256=sha(data),source=path,commit=BASE)
    for path in sorted((HERE/'fixtures').glob('*')):
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes();write(out/'fixtures'/path.name,data)
        fixtures[path.name] = dict(sha256=sha(data),source=str(path.relative_to(REPOSITORY)))
    # Concrete real Rust inputs cross the existing budgets; no AST model or
    # hand-constructed AST is used for these boundary fixtures.
    generated = {
        'literal-budget.rs': '#![allow(dead_code)]\nfn rejected_literal_budget() -> &\'static str { "'+'x'*131073+'" }\nfn main() {}\n',
        'source-budget.rs': '#![allow(dead_code)]\nfn rejected_source_budget() -> u32 { /*'+'x'*262144+'*/ 1 }\nfn main() {}\n',
        'node-budget.rs': '#![allow(dead_code, unused)]\nfn rejected_node_budget() -> u32 { '+'0;'*4200+' 1 }\nfn main() {}\n',
        'depth-budget.rs': '#![allow(dead_code, unused_parens)]\nfn rejected_depth_budget() -> u32 { '+'('*130+'1'+')'*130+' }\nfn main() {}\n',
        'identifier-budget.rs': '#![allow(dead_code, unused)]\nfn rejected_identifier_budget('+'x'*4097+':u32) {}\nfn main() {}\n',
    }
    for name,text in generated.items():
        data=text.encode();write(out/'fixtures'/name,data)
        fixtures[name]=dict(sha256=sha(data),generated_by='prepare.py')
    manifest = dict(schema_version=1,status='source-only-uncompiled-unrun',audit_only=True,
        timing_eligible=False,benchmark=False,performance_measurements=0,compiler_builds=0,
        qualification_run=False,base_commit=BASE,performance_artifact_commit=ARTIFACT_COMMIT,
        performance_patch_sha256=inherited['patch_sha256'],performance_identity=inherited['source_identity'],
        source_identity=identity,patch_sha256=sha(patch),old_function_sha256=sha(old_function.encode()),
        changed_files=changed,before_hashes={n:sha(before[n]) for n in changed},
        audit_hashes={n:sha(after[n]) for n in changed},acyclic_identity_files=closure,
        fixtures=fixtures,generator_sha256=sha(Path(__file__).read_bytes()))
    write(out/'manifest.json',(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps(dict(status=manifest['status'],audit_only=True,timing_eligible=False,
        source_identity=identity,patch_sha256=sha(patch),manifest_sha256=sha((out/'manifest.json').read_bytes()),
        fixtures=len(fixtures)),indent=2))


if __name__ == '__main__':
    main()

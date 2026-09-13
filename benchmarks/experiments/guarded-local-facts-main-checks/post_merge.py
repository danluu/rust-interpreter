"""Check later main integration without rebuilding unchanged Rust components."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from component import ROOT
from compare_saved_runtime import acquire_lock, sha
from inputs import rust_input
from workflow_io import capture, require_space, write_json as write


def other_functions(source):
    module = ast.parse(source)
    matched = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'tree_stamps']
    assert len(matched) == 1
    module.body.remove(matched[0])
    return ast.dump(module, include_attributes=False)


def main():
    run = 'guarded-local-facts-main-post-merge-01'
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        source = ROOT / '.work/publication-main'
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=source).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        build_path = ROOT / 'results/guarded-local-facts-main-build-01/summary.json'
        audit_path = ROOT / 'results/guarded-local-facts-main-final-audit-01/summary.json'
        build, audit = [json.loads(p.read_text()) for p in [build_path, audit_path]]
        assert audit['status'] == 'passed' and audit['all_frozen_inputs_verified']
        assert audit['tool_key'] == build['tool_key'] and audit['binaries'] == build['binaries']
        assert all(c['exact'] for c in audit['project_artifact_identity'])
        raw = ROOT / build['raw']
        assert sha(raw / 'plan.json') == build['plan_sha256']
        plan = json.loads((raw / 'plan.json').read_text())
        tracked = [p for p in subprocess.check_output(['git', 'ls-files', '-z'], cwd=source).decode().split('\0') if p]
        current = {p: sha(source / p) for p in tracked if rust_input(p)}
        assert current == plan['rust_inputs'], 'merged Rust/compiler inputs changed'
        assert all(sha(ROOT / p) == digest for p, digest in current.items())
        for name, digest in build['binaries'].items():
            assert sha(ROOT / '.work/interpreter-tools' / build['tool_key'] / name) == digest
        prefix = '.work/publication-main/'
        previous = {p[len(prefix):]: h for p, h in plan['frozen'].items()
                    if p.startswith(prefix + 'scripts/') or p.startswith(prefix + '.cargo/')}
        new = {p: sha(source / p) for p in tracked if p.startswith(('scripts/', '.cargo/'))}
        assert set(previous) == set(new)
        changed = [p for p in new if new[p] != previous[p]]
        assert changed == ['scripts/custom_compiler.py'], changed
        old_loader = subprocess.check_output(['git', 'show', build['source_commit'] + ':' + changed[0]], cwd=ROOT)
        assert other_functions(old_loader) == other_functions((source / changed[0]).read_bytes())
        # The new main code changes only owned custom-compiler tree inspection;
        # the stock route used by the completed histories and all other loader
        # functions are unchanged. Retain its six explicit new boundary tests.
        assert sha(ROOT / changed[0]) == new[changed[0]]
        paths = [source / p for p in tracked if p.startswith(('scripts/', 'tests/', '.cargo/')) or rust_input(p)]
        paths += [Path(__file__), build_path, audit_path, raw / 'plan.json']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=revision, source=str(source),
            frozen=frozen, command=command, unchanged_rust_inputs=len(current),
            changed_launcher_helpers=changed, changed_loader_function='tree_stamps',
            tool_key=build['tool_key'], performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        child, out, err = capture(command, cwd=source, env=env,
            receipt_path=work / 'active.json', receipt=dict(stage='merged Python contracts'))
        (work / 'stdout').write_text(out); (work / 'stderr').write_text(err)
        write(work / 'record.json', dict(pid=child.pid, command=command, returncode=child.returncode,
            stdout_sha256=sha(work / 'stdout'), stderr_sha256=sha(work / 'stderr')))
        assert child.returncode == 0, err[-3000:]
        count, = re.findall(r'Ran (\d+) tests? in ', err)
        assert int(count) >= 334 and err.rstrip().endswith('OK (skipped=16)')
        owned = re.findall(r'^test_\S+ \(test_owned_tree_stamps\.[^\n]+\) \.\.\. ok$', err, re.M)
        assert len(owned) == 6
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision
        result = ROOT / 'results' / run
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_commit=revision, commands=1,
            tests=int(count), skipped=16, owned_tree_boundary_tests=6, tool_key=build['tool_key'],
            unchanged_rust_inputs=len(current), unchanged_executed_stock_route=True,
            preserved_main_loader_change='tree_stamps', raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), record_sha256=sha(work / 'record.json'), performance_measurement=False))
        print('PASS: merged Python contracts and unchanged Rust/tool/stock-route inputs', flush=True)


if __name__ == '__main__': main()

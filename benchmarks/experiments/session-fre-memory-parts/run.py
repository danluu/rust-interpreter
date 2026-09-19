"""Reconstruct memory subparts of two closed captures without executing guests."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
NAME = 'session-fre-memory-parts-01'


def read(p):
    return json.loads(p.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        closed_path=ROOT/'results/session-fre-runtime-sampling-01/closure.json';summary_path=closed_path.with_name('summary.json')
        closed,summary=read(closed_path),read(summary_path)
        assert closed['status']=='closed' and closed['all_hashes_verified'] and summary['status']=='passed'
        assert sha(summary_path)==closed['summary_sha256']
        bindings_path=ROOT/closed['evidence'];assert sha(bindings_path)==closed['evidence_sha256']
        paths=[closed_path,summary_path,bindings_path]
        for p,h in read(bindings_path).items():assert sha(ROOT/p)==h;paths.append(ROOT/p)
        build_path=ROOT/'results/session-duration-order-qualification-02/summary.json';build=read(build_path)
        closure=build_path.with_name('closure.json');c=read(closure)
        assert c['status']=='closed' and c['all_hashes_verified'] and sha(build_path)==c['summary_sha256'];paths.append(closure)
        assert build['tests']['debug']==build['tests']['release']==dict(passed=679,ignored=17)
        build_plan=ROOT/build['raw']/'plan.json';assert sha(build_plan)==build['plan_sha256']
        for name,digest in read(build_plan)['frozen'].items():
            if name.startswith('crates/') or name in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:
                assert sha(ROOT/name)==digest;paths.append(ROOT/name)
        qualified_rows=ROOT/build['raw']/'records.json';assert sha(qualified_rows)==build['records_sha256'];paths.append(qualified_rows)
        for label in ['debug','release']:
            row,=[r for r in read(qualified_rows) if r['label']==label];assert row['returncode']==0
            log=ROOT/'.work/session-duration-order-qualification-01'/(label+'.stdout')
            assert sha(log)==row['stdout_sha256'];paths.append(log)
            for test in ['memory_parts_separate_dynamic_address_checks_without_changing_words',
                    'memory_parts_preserve_shared_frame_forwarding_and_odd_transfers',
                    'memory_parts_stop_at_operations_and_exclude_fills_and_large_copies',
                    'memory_parts_preserve_scalar_call_targets_without_publishing_code']:
                assert '::'+test+' ... ok' in log.read_text()
        prior = ROOT / '.work/scalar-memory-parts-01'
        prior_plan, prior_rows = read(prior / 'plan.json'), read(prior / 'records.json')
        control, = [r for r in prior_rows if r['label'] == 'python-controls']
        assert control['returncode'] == 0 and sha(prior / 'python-controls.stderr') == control['stderr_sha256']
        assert 'Ran 2 tests' in (prior / 'python-controls.stderr').read_text()
        import ast
        def functions(path):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name in ['locate', 'identity']}
        old_attribute = ROOT / 'benchmarks/experiments/scalar-memory-parts/attribute.py'
        assert functions(old_attribute) == functions(Path(__file__).with_name('attribute.py'))
        for name in ['attribute.py', 'test_parts.py']:
            path = ROOT / 'benchmarks/experiments/scalar-memory-parts' / name
            assert sha(path) == prior_plan['frozen'][str(path.relative_to(ROOT))]
            paths.append(path)
        paths += [build_path, build_plan, prior / 'plan.json', prior / 'records.json', prior / 'python-controls.stderr']
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines()]
        paths += [ROOT / 'scripts' / p for p in ['compare_saved_runtime.py', 'workflow_io.py', 'summarize_owned_sample.py']]
        artifact = ROOT / '.work/session-project-edit-token-01/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        assert sha(artifact) == artifact.stem
        paths.append(artifact)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            target=str(target.relative_to(ROOT)), same_source_root=True, required_free_bytes=needed,
            allocated_target_bytes=allocated, minimum_child_gib=8, reused_controls=6, expected_commands=3,
            guest_commands=0, executable_code_publications=0, production_runtime_changes=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'MEMORY_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', RUST_TEST_THREADS='2', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--release', '--lib', '-p', 'rust-interp-bytecode', '--features', 'jit-session-duration-order',
                 '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(target)]
        test = 'jit::code_spans::memory_parts::'
        commands = []
        for label in ['block', 'exhaustive']:
            folder = ROOT / '.work' / ('session-fre-sample-' + label + '-01') / '0'
            commands.append((label, [*cargo, test + 'observe_saved_small_memory_parts', '--', '--ignored', '--exact'],
                dict(MEMORY_ARTIFACT=str(artifact), MEMORY_MAP=str(folder / 'jit-code/operations.json'),
                     MEMORY_CODE=str(folder / 'jit-code/code.bin'), MEMORY_OUTPUT=str(work / (label + '.json'))), ROOT, 1))
        commands.append(('attribute', [sys.executable, str(Path(__file__).with_name('attribute.py')), NAME], {}, ROOT, 0))
        records = [];write(work/'records.json',records)
        for label, command, extra, cwd, tests in commands:
            require_space(ROOT, 8)
            if command[0] == 'cargo':
                assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            start = time.time()
            child, out, err = capture(command, cwd=cwd, env=env | extra, receipt_path=work / 'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]:
                (work / (label + '.' + stream)).write_text(payload)
            records.append(dict(label=label, command=command, extra_env=extra, pid=child.pid,
                returncode=child.returncode, seconds=time.time() - start,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            if tests:
                if label == 'python-controls':
                    assert 'Ran 2 tests' in err and err.rstrip().endswith('OK')
                else:
                    assert f'test result: ok. {tests} passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        out = ROOT / 'results' / NAME
        report = read(out / 'attribution.json')
        assert report['status'] == 'passed' and len(report['cases']) == 2
        write(out / 'summary.json', dict(status='passed', commands=3, reused_controls=6, cases=[{k: c[k] for k in
            ['case', 'ordinary_functions', 'scalar_bodies', 'memory_part_spans', 'generated_samples', 'selected_samples', 'samples_by_part', 'copy_samples_by_part']} for c in report['cases']],
            setup_seconds=sum(r['seconds'] for r in records), source_revision=revision, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            attribution_sha256=sha(out / 'attribution.json'), census_sha256={l: sha(work / (l + '.json')) for l in ['block', 'exhaustive']},
            outputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'attribution.json',work/'block.json',work/'exhaustive.json']},
            guest_commands=0, executable_code_publications=0, production_runtime_changes=0, performance_measurement=False))


if __name__ == '__main__':
    if sys.argv[1:]==['--close']:
        sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
        import focus
        focus.RUN=NAME;focus.close()
    else:
        assert len(sys.argv)==1
        main()

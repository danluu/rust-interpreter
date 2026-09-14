"""Qualify staged words first, then native controls under serialized admission."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

def read(p): return json.loads(p.read_text())

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['static', 'native'], required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch('native-continuation-snapshot-' + args.stage + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        paths = [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines()]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / 'scripts' / p for p in ['workflow_io.py', 'compare_saved_runtime.py']]
        if args.stage == 'native':
            folder = ROOT / 'results/native-continuation-snapshot-static-01'
            closed = read(folder / 'closure.json'); prior = read(folder / 'summary.json')
            assert closed['status'] == 'closed' and closed['all_hashes_verified']
            assert sha(folder / 'summary.json') == closed['summary_sha256']
            assert prior['status'] == 'passed' and prior['tests'] == {'debug': 3, 'release': 3}
            prior_plan = ROOT / prior['raw'] / 'plan.json'; assert sha(prior_plan) == prior['plan_sha256']
            for p, h in read(prior_plan)['frozen'].items():
                if p.startswith('crates/'): assert sha(ROOT / p) == h, p
            paths += [folder / 'summary.json', folder / 'closure.json', prior_plan]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        clang = Path(subprocess.check_output(['xcrun', '--find', 'clang'], text=True).strip()).resolve()
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        tests, ignored = (3, 0) if args.stage == 'static' else (349, 11)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, stage=args.stage,
            frozen=frozen, target=str(target.relative_to(ROOT)), same_source_root=True,
            required_free_bytes=needed, allocated_target_bytes=allocated, minimum_child_gib=8,
            expected_commands=2, tests_per_profile=tests, ignored_per_profile=ignored,
            original_project_guest_commands=0, native_guest_unit_tests=args.stage=='native',
            executable_code_published_in_tests=args.stage=='native', prototype_runtime_source_changed=True,
            performance_measurement=False, assembler=str(clang), assembler_sha256=sha(clang)))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
            and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', RUST_TEST_THREADS='2', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--lib', '-p', 'rust-interp-bytecode',
            '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT/'Cargo.toml'), '--target-dir', str(target)]
        suffix = ['jit::continuations::tests::', '--', '--skip', 'native_snapshots', '--nocapture'] if args.stage=='static' else ['--', '--nocapture']
        records = []
        for label in ['debug', 'release']:
            require_space(ROOT, 8); assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            command = cargo + (['--release'] if label=='release' else []) + suffix
            start = time.time()
            child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work/'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]: (work/(label+'.'+stream)).write_text(payload)
            oracles = []
            for match in re.finditer(r'independent assembler object: (.+/oracle\.o) \((\d+) words\)', out):
                obj = Path(match[1]); copies = {}
                for name in ['oracle.s', 'oracle.o']:
                    source = obj.with_name(name); destination = work/(label+'-'+name)
                    assert not destination.exists(); shutil.copy2(source, destination)
                    copies[str(destination.relative_to(ROOT))] = sha(destination)
                oracles.append(dict(original_path=str(obj), words=int(match[2]), copies=copies))
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                seconds=time.time()-start, oracles=oracles,
                stdout_sha256=sha(work/(label+'.stdout')), stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json', records)
            assert child.returncode==0, (out+err)[-7000:]
            assert f'test result: ok. {tests} passed; 0 failed; {ignored} ignored;' in out, out[-1500:]
            assert len(oracles)==1
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label, tests, 'passed', flush=True)
        assert sha(clang)==read(work/'plan.json')['assembler_sha256']
        result = ROOT/'results'/args.run_id; result.mkdir(exist_ok=False)
        write(result/'summary.json', dict(status='passed', stage=args.stage, source_revision=revision,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work/'plan.json'), records_sha256=sha(work/'records.json'),
            commands=2, tests={r['label']:tests for r in records}, ignored_per_profile=ignored,
            setup_seconds=sum(r['seconds'] for r in records), original_project_guest_commands=0,
            native_guest_unit_tests=args.stage=='native', executable_code_published_in_tests=args.stage=='native',
            prototype_runtime_source_changed=True, performance_measurement=False))

if __name__ == '__main__': main()

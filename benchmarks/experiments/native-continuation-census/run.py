"""Qualify test-only continuation inspection and reconstruct two adopted captures offline."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['build', 'census'], required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch('native-continuation-' + args.stage + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12 if args.stage == 'build' else 8)
        paths = [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and p.suffix in ['.rs', '.toml']]
        paths += [ROOT / n for n in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml',
            'scripts/compare_saved_runtime.py', 'scripts/workflow_io.py', 'scripts/summarize_owned_sample.py',
            'scripts/profile_vm_transitions.py',
            'results/adopted-runtime-sampling-01/source-bindings.json']]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.md', '.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        rust = {p: h for p, h in frozen.items() if p.startswith('crates/') or p in
                ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml']}
        commands = []
        extra_env = []
        if args.stage == 'build':
            for label, flags in [('debug', []), ('release', ['--release'])]:
                commands.append((label, ['cargo', '+nightly-2026-09-08', 'test', *flags,
                    '--locked', '--offline', '--jobs', '2', '--target-dir', str(TARGET),
                    '-p', 'rust-interp-bytecode']))
                extra_env.append({})
        else:
            build_path = ROOT / 'results/native-continuation-build-02/summary.json'
            build = json.loads(build_path.read_text())
            assert build['status'] == 'passed' and build['rust_inputs'] == rust
            frozen[str(build_path.relative_to(ROOT))] = sha(build_path)
            profile_proof=ROOT/'results/guarded-local-facts-profile-01/summary.json'
            proof=json.loads(profile_proof.read_text());assert proof['status']=='passed'
            frozen[str(profile_proof.relative_to(ROOT))]=sha(profile_proof)
            profile_plan=ROOT/proof['raw']/'plan.json'
            assert sha(profile_plan)==proof['plan_sha256']
            frozen[str(profile_plan.relative_to(ROOT))]=sha(profile_plan)
            protocol_proof=ROOT/'results/native-protocol-census-01/attribution.json'
            protocol=json.loads(protocol_proof.read_text());assert protocol['status']=='passed'
            frozen[str(protocol_proof.relative_to(ROOT))]=sha(protocol_proof)
            for index,label in enumerate(['block','exhaustive']):
                raw=ROOT/proof['raw']/(str(index)+'-profile.json')
                assert sha(raw)==proof['comparisons'][index]['profile_sha256']
                frozen[str(raw.relative_to(ROOT))]=sha(raw)
                for name,h in protocol['cases'][index]['evidence'].items():
                    assert sha(ROOT/name)==h;frozen[name]=h
            artifact = ROOT / '.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
            assert sha(artifact) == artifact.stem
            assert json.loads(profile_plan.read_text())['frozen'][str(artifact.relative_to(ROOT))]==artifact.stem
            frozen[str(artifact.relative_to(ROOT))] = sha(artifact)
            for label in ['block', 'exhaustive']:
                folder = ROOT / '.work' / ('adopted-runtime-sample-' + label + '-01') / '0'
                record_path = folder / 'record.json'
                record = json.loads(record_path.read_text())
                assert record['identity']['status'] == 'finished' and record['identity']['returncode'] == 0
                assert '--profile' not in record['identity']['command']
                frozen[str(record_path.relative_to(ROOT))] = sha(record_path)
                for p, h in record['files'].items():
                    assert sha(folder / p) == h
                    frozen[str((folder / p).relative_to(ROOT))] = h
                commands.append((label, ['cargo', '+nightly-2026-09-08', 'test', '--release',
                    '--locked', '--offline', '--jobs', '2', '--target-dir', str(TARGET),
                    '-p', 'rust-interp-bytecode', '--lib',
                    'jit::code_spans::continuation_census::observe_saved_native_continuations', '--', '--ignored', '--exact']))
                extra_env.append(dict(CONTINUATION_ARTIFACT=str(artifact), CONTINUATION_MAP=str(folder / 'jit-code/operations.json'),
                    CONTINUATION_CODE=str(folder / 'jit-code/code.bin'),
                    CONTINUATION_OUTPUT=str(ROOT / '.work' / args.run_id / (label + '.json'))))
            commands.append(('attribute', [sys.executable, str(Path(__file__).with_name('attribute.py')),
                '--run-id', args.run_id]))
            extra_env.append({})
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], text=True).strip(), frozen=frozen, rust_inputs=rust,
            commands=[dict(label=l, command=c, extra_env=e) for (l, c), e in zip(commands, extra_env)],
            guest_benchmark_commands=0, performance_measurement=False, minimum_child_free_gib=8))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'CONTINUATION_'))
            and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                          'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_BUILD_JOBS='2', PYTHONDONTWRITEBYTECODE='1',
            CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0', CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records = []
        for (label, command), extra in zip(commands, extra_env):
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=ROOT, env=env | extra,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            record = dict(label=label, command=command, pid=child.pid, returncode=child.returncode, stdout=out, stderr=err)
            records.append(record)
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-4500:]
            if args.stage == 'build':
                for name in ['continuation_census_distinguishes_native_unsupported_and_one_past_returns',
                             'continuation_census_checks_proposed_offset_field_without_changing_frame_layout']:
                    assert '::' + name + ' ... ok' in out
                record['tests_passed'] = sum(map(int, re.findall(r'test result: ok\. (\d+) passed;', out)))
                assert record['tests_passed']==414, record['tests_passed']
                write(work / 'records.json', records)
            print(label, 'passed', flush=True)
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=True)
        write(result / 'summary.json', dict(status='passed', rust_inputs=rust, commands=len(records),
            tests={r['label']: r['tests_passed'] for r in records if 'tests_passed' in r},
            guest_benchmark_commands=0, performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__': main()

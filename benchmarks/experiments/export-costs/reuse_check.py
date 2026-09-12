#!/usr/bin/env python3
"""Check function-census transparency and strict rejection on original fixtures."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools, TOOLCHAIN
from std_mir import checked_std_mir
from workflow_io import capture, require_space, write_json as write
from reuse_build import CONTROL


def observation(stderr, artifact):
    prefix = 'rust-interp-function-costs: '
    lines = [line[len(prefix):] for line in stderr.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1 and len(lines[0].encode()) <= 16 * 1024**2
    result = json.loads(lines[0])
    assert result['schema_version'] == 1 and result['complete'] is True
    assert result['artifact_sha256'] == sha(artifact)
    rows = result['functions']
    assert 0 < len(rows) == result['observed_functions'] <= result['program_functions'] <= 10_257
    assert result['unobserved_functions'] == result['program_functions'] - len(rows)
    assert len({row['index'] for row in rows}) == len(rows)
    for row in rows:
        assert type(row['index']) is int and 0 <= row['index'] < result['program_functions']
        assert row['name'] and all(re.fullmatch('[0-9a-f]{64}', row[key]) for key in ['lowered_sha256', 'final_sha256'])
        assert all(math.isfinite(row[key]) and row[key] >= 0 for key in ['prepare_seconds', 'lower_seconds'])
        assert all(type(row[key]) is int and row[key] >= 0 for key in ['mir_locals', 'mir_blocks', 'lowered_operations', 'final_operations'])
    prefix = 'rust-interp-export-timings: '
    scopes = [json.loads(line[len(prefix):]) for line in stderr.splitlines() if line.startswith(prefix)]
    assert len(scopes) == 2 and {s['scope'] for s in scopes} == {'emit', 'lower'}
    for scope in scopes:
        assert abs(sum(s['seconds'] for s in scope['stages']) - scope['total_seconds']) < 1e-8
    stage = next(s['seconds'] for scope in scopes if scope['scope'] == 'lower'
                 for s in scope['stages'] if s['name'] == 'reachable_mir_and_local_passes')
    assert sum(row['prepare_seconds'] + row['lower_seconds'] for row in rows) <= stage
    return result, scopes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'export-reuse-fixtures-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build = json.loads(args.build.read_text())
        assert build['status'] == 'passed' and set(build['tests'].values()) == {41}
        tool, key = installed_tools(build['tool_key'])
        baseline, _ = installed_tools(CONTROL)
        sysroot, _, std_key, _ = checked_std_mir(TOOLCHAIN)
        assert std_key == 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        fixtures = ['scalar_constant', 'static', 'tls', 'caller']
        paths = [Path(__file__), args.build.resolve(), ROOT / 'benchmarks/experiments/export-costs/REUSE.md']
        paths += [ROOT / 'tests' / (f + '_fixture.rs') for f in fixtures]
        paths += [p / name for p in [tool, baseline] for name in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, source_commit=build['source_commit'], tool_key=key,
              baseline_tool_key=CONTROL, std_mir_key=std_key, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL']}
        records, reports = [], []
        def invoke(label, command, selected=env, success=True):
            command = list(map(str, command))
            child, stdout, stderr = capture(command, cwd=ROOT, env=selected,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            record = dict(label=label, command=command, pid=child.pid, returncode=child.returncode)
            for suffix, text in [('stdout', stdout), ('stderr', stderr)]:
                path = work / (label + '.' + suffix)
                path.write_text(text)
                record[suffix] = str(path.relative_to(ROOT))
                record[suffix + '_sha256'] = sha(path)
            records.append(record)
            write(work / 'records.json', records)
            assert (child.returncode == 0) == success, label
            return stdout, stderr
        seeds = ['0', '7', str(2**64 - 1)]
        for name in fixtures:
            source = ROOT / 'tests' / (name + '_fixture.rs')
            native = work / (name + '-native')
            invoke(name + '-native-build', ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', native])
            expected = {seed: invoke(name + '-native-' + seed, [native, seed])[0] for seed in seeds}
            hashes = []
            for label, compiler, enabled in [('retained', baseline, False), ('off', tool, False), ('on', tool, True)]:
                artifact = work / (name + '-' + label + '.rbc')
                selected = dict(env, RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='rust_interp_entry')
                if enabled:
                    selected.update(RUST_INTERP_FUNCTION_COSTS='1', RUST_INTERP_EXPORT_TIMINGS='1')
                invoke_label = name + '-export-' + label
                _, stderr = invoke(invoke_label, [compiler / 'rust-interp-mir-export', source, '--crate-name',
                    'reuse_census_case', '--edition=2024', '--emit=metadata', '--sysroot', sysroot,
                    '-o', artifact.with_suffix('.rmeta')], selected)
                hashes.append(sha(artifact))
                if enabled:
                    report, scopes = observation(stderr, artifact)
                    write(work / (name + '-census.json'), report)
                    reports.append(dict(fixture=name, artifact_sha256=sha(artifact),
                        observed_functions=report['observed_functions'], program_functions=report['program_functions'],
                        report_sha256=sha(work / (name + '-census.json'))))
                else:
                    assert 'rust-interp-function-costs:' not in stderr
                for engine in ['interpreter', 'jit']:
                    flags = ['--jit-resumable-calls', '--jit-persistent-registers'] if engine == 'jit' else []
                    for seed in seeds:
                        stdout, _ = invoke(name + '-' + label + '-' + engine + '-' + seed,
                                           [tool / 'rust-interp-vm', '--engine', engine, *flags, artifact, seed])
                        assert stdout == expected[seed]
            assert len(set(hashes)) == 1, 'observer changed original artifact'
        for name, body, settings, diagnostic in [
            ('type', 'fn unused() { let _: u64 = "wrong"; }', {}, 'mismatched types'),
            ('borrow', 'fn unused() { let mut x=1; let a=&mut x; let b=&mut x; *a+=*b; }', {}, 'cannot borrow'),
            ('invalid-option', '', {'RUST_INTERP_FUNCTION_COSTS': 'invalid'}, 'must be 0 or 1'),
            ('partial-checking', '', {'RUST_INTERP_DEMAND_BODIES': '1'}, 'require strict checking'),
        ]:
            source = work / (name + '.rs')
            source.write_text('pub fn entry() -> u64 { 1 }\n' + body + '\n')
            artifact = work / (name + '.rbc')
            artifact.write_bytes(b'stale artifact')
            selected = dict(env, RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='entry', RUST_INTERP_FUNCTION_COSTS='1')
            selected.update(settings)
            _, stderr = invoke('reject-' + name, [tool / 'rust-interp-mir-export', source,
                '--crate-type=lib', '--edition=2024', '--emit=metadata', '-o', artifact.with_suffix('.rmeta')], selected, success=False)
            assert diagnostic in stderr and not artifact.exists() and 'rust-interp-function-costs:' not in stderr
        assert all(sha(ROOT / path) == digest for path, digest in frozen.items())
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', performance_measurement=False, tool_key=key,
              source_commit=build['source_commit'], commands=len(records), native_executions=12, guest_executions=72,
              exports=12, native_builds=4, expected_rejections=4, fixtures=reports,
              all_artifact_hashes_identical=True, frozen=frozen, raw=str(work.relative_to(ROOT)),
              records_sha256=sha(work / 'records.json')))
        print('PASS', len(records), 'commands; four original fixtures; exact artifacts; strict rejections')


if __name__ == '__main__':
    main()

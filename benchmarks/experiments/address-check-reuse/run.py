#!/usr/bin/env python3
"""Count repeated checks from typed saved inputs; no guest execution."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'address-check-reuse-census-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        build_path = args.build.resolve(strict=True)
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed' and not build['emitter_changed']
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=426, ignored=1)
        binary = ROOT / build['binary']
        assert sha(binary) == build['binary_sha256']
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        reference = json.loads(reference_path.read_text())
        wide_path = ROOT / 'results/wide-bitwise-profile-01/summary.json'
        wide = json.loads(wide_path.read_text())
        assert reference['status'] == wide['status'] == 'passed'
        assert reference['exact_logical_counts_memory_and_entropy'] and wide['exact_logical_counts_memory_and_entropy']
        wide_raw = ROOT / wide['raw']
        assert sha(wide_raw / 'records.json') == wide['records_sha256']
        paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), build_path, binary,
            reference_path, wide_path, wide_raw / 'records.json',
            ROOT / 'scripts/workflow_io.py', ROOT / 'scripts/compare_saved_runtime.py']
        inputs = []
        for item in reference['profiles']:
            prior, = [c for c in wide['comparisons'] if c['index'] == item['index']]
            artifact = ROOT / item['artifact']
            profile = wide_raw / f"{item['index']}-profile.json"
            assert sha(artifact) == item['artifact_sha256'] and sha(profile) == prior['profile_sha256']
            inputs.append(dict(index=item['index'], name=item['name'], artifact=str(artifact),
                profile=str(profile), artifact_sha256=sha(artifact), profile_sha256=sha(profile)))
            paths += [artifact, profile]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, inputs=inputs,
            expected_commands=10, guest_executions=0, performance_measurement=False,
            semantics='Observational same-register range cache,16 entries; no emitter change.'))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        records, comparisons = [], []

        def invoke(label, artifact, output, profile, success, message=None):
            require_space(ROOT, 8)
            command = list(map(str, [binary, artifact, output, profile]))
            before = sha(output) if output.exists() else None
            child, out, err = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            records.append(dict(label=label, command=command, pid=child.pid,
                returncode=child.returncode, stdout=out, stderr=err, expected_success=success))
            write(work / 'records.json', records)
            assert (child.returncode == 0) == success, err
            if message:
                messages = (message,) if isinstance(message, str) else message
                assert any(m in err for m in messages), err
            assert not out
            if not success:
                assert (sha(output) if output.exists() else None) == before
            return output

        for item in inputs:
            output = work / f"{item['index']}-census.json"
            invoke(f"census-{item['index']}", item['artifact'], output, item['profile'], True)
            report = json.loads(output.read_text())
            assert report['status'] == 'counted' and report['guest_instructions_executed'] == 0
            assert report['emitter_changed'] is False and report['cache_entries'] == 16
            assert all(report[k] == item[k] for k in ['artifact_sha256', 'profile_sha256'])
            counts = report['counts']
            assert counts['known_local'] + counts['baseline_checks'] == counts['accesses']
            assert counts['reusable_checks'] + counts['permission_upgrades'] <= counts['baseline_checks']
            assert all(sum(f['counts'][key] for f in report['functions']) == value for key, value in counts.items())
            comparisons.append(dict(index=item['index'], name=item['name'], counts=counts,
                declined_functions=len(report['declined_functions']), analysis_work=report['analysis_work'],
                report_sha256=sha(output), top_functions=report['functions'][:15]))
            print(item['index'], 'counted', counts, flush=True)
        first = inputs[0]
        bad = work / 'empty.rbc'; bad.write_bytes(b'')
        mismatch = work / 'mismatch.json'; mismatch.write_text('{"functions": []}\n')
        large_bc = work / 'oversized.rbc'
        with large_bc.open('xb') as f: f.truncate(64 * 1024**2 + 1)
        large_profile = work / 'oversized.json'
        with large_profile.open('xb') as f: f.truncate(256 * 1024**2 + 1)
        directory = work / 'directory'; directory.mkdir()
        link = work / 'symlink.rbc'; link.symlink_to(first['artifact'])
        cases = [('empty', bad, first['profile'], ('UnexpectedEof', 'unexpected end')),
            ('mismatched', first['artifact'], mismatch, 'profile function count mismatch'),
            ('oversized-bytecode', large_bc, first['profile'], 'bounded regular file'),
            ('oversized-profile', first['artifact'], large_profile, 'bounded regular file'),
            ('directory', directory, first['profile'], 'bounded regular file'),
            ('symlink', link, first['profile'], 'bounded regular file')]
        for label, artifact, profile, message in cases:
            invoke(label, artifact, work / (label + '-unexpected-output.json'), profile, False, message)
        invoke('existing-output', first['artifact'], work / '0-census.json', first['profile'], False, 'AlreadyExists')
        assert len(records) == 10 and all(sha(ROOT / p) == h for p,h in frozen.items())
        destination = ROOT / 'results' / args.run_id
        destination.mkdir(exist_ok=False)
        result = dict(status='passed', commands=len(records), guest_executions=0,
            typed_profile_cases=3, cli_rejection_controls=7, comparisons=comparisons,
            raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), binary_sha256=sha(binary),
            performance_measurement=False, emitter_changed=False)
        write(destination / 'summary.json', result)
        print('PASS three typed censuses and seven CLI rejection controls', flush=True)


if __name__ == '__main__':
    main()

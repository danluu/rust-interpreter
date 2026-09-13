"""Inspect one original parser test with the qualified immutable runtime."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from profile_vm_transitions import counts
from workflow_io import capture, require_space, write_json as write
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/operation-map'))
from maps import validate as validate_map


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'parser-runtime-profile-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        proof_path = ROOT / 'results/pgrust-parser-edits-incremental-history-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['commands'] == 66 and proof['source_restored']
        raw = ROOT / proof['raw']
        assert sha(raw / 'records.json') == proof['records_sha256']
        row, = [r for r in json.loads((raw / 'records.json').read_text())
                if r['cycle'] == 3 and r['state'] == 0 and r['mode'] == 'custom-a']
        artifact, catalog = [ROOT / row[k]['path'] for k in ['artifact', 'entry_catalog']]
        for k, p in [('artifact', artifact), ('entry_catalog', catalog)]:
            assert sha(p) == row[k]['sha256']
        build_path = ROOT / 'results/environment-read-frontend-build-01/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed' and build['tool_key'] == proof['tool_key']
        vm = ROOT / '.work/interpreter-tools' / proof['tool_key'] / 'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        paths = [Path(__file__), Path(__file__).with_name('PARSER-RUNTIME.md'), proof_path,
                 raw / 'records.json', artifact, catalog, build_path, vm]
        paths += [ROOT / 'scripts' / name for name in
                  ['profile_vm_transitions.py', 'workflow_io.py', 'compare_saved_runtime.py']]
        paths.append(ROOT / 'benchmarks/experiments/operation-map/maps.py')
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        name = 'tests_dump::c_reference_vectors'
        command = [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                   '--instruction-limit', '100000000000', '--allocation-limit', '150000',
                   '--profile', str(work / 'profile.json'), '--profile-test', name,
                   '--suite-catalog', str(catalog), '--jit-code-dump', str(work / 'code'),
                   '--jit-operation-map', str(artifact)]
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, command=command,
            expected_commands=1, test=name, reference_row=row['index'], minimum_free_gib=8,
            performance_measurement=False, fresh_owner_differs_from_prepared_suite=True))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env['RUST_INTERP_VM_STATS'] = '1'
        child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json', receipt={})
        write(work / 'records.json', [dict(pid=child.pid, command=command,
              returncode=child.returncode, stdout=out, stderr=err)])
        assert child.returncode == 0 and out == '0\n', err
        selection, = [json.loads(s.split(': ', 1)[1]) for s in err.splitlines()
                      if s.startswith('rust-interp-profile-selection: ')]
        stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', err)}
        assert (work / 'profile.json').stat().st_size <= 256 * 1024**2
        profile = json.loads((work / 'profile.json').read_text())
        attribution = counts(profile, stats)
        dump = json.loads((work / 'code/map.json').read_text())
        assert dump['pid'] == child.pid and dump['profiled'] and dump['resumable_calls']
        assert dump['persistent_registers'] and dump['code_bytes'] == stats['jit_bytes']
        mapping = json.loads((work / 'code/operations.json').read_text())
        validate_map(mapping, dump, (work / 'code/code.bin').read_bytes(), profile, child.pid)
        published = {r['function'] for r in mapping['functions']}
        unpublished = [dict(function=i, name=f['name'], operations=len(f['operations']),
                            interpreted=sum(f['interpreted']))
                       for i, f in enumerate(profile['functions'])
                       if i not in published and sum(f['interpreted'])]
        unpublished.sort(key=lambda r: -r['interpreted'])
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=1, test=name,
            tool_key=proof['tool_key'], vm_sha256=sha(vm), selection=selection, statistics=stats,
            attribution=attribution, executed_without_published_code=unpublished,
            exact_operation_map_reconstruction=True, raw=str(work.relative_to(ROOT)),
            evidence={str(p.relative_to(work)): sha(p) for p in
                      [work / 'plan.json', work / 'records.json', work / 'active.json',
                       work / 'profile.json', work / 'code/code.bin', work / 'code/map.json',
                       work / 'code/operations.json']}, performance_measurement=False,
            fresh_owner_differs_from_prepared_suite=True))
        print(json.dumps(dict(statistics=stats, executed_without_published_code=unpublished)), flush=True)


if __name__ == '__main__':
    main()

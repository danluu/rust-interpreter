#!/usr/bin/env python3
"""Qualify three operation maps against exact retained adopted code and profiles."""
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
from maps import validate


def exact_profile(current, previous):
    assert current == previous, 'retained per-PC profile changed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'operation-map-real-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        build_path = args.build.resolve(strict=True)
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed'
        assert build['tests']['test-debug'] == build['tests']['test-release'] == dict(passed=436, ignored=1)
        assert build['composition']['exporter_and_wrapper_key'] == 'e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846'
        vm = ROOT / '.work/interpreter-tools' / build['tool_key'] / 'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        proof_path = ROOT / 'results/operation-map-qualification-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['commands'] == 7 and proof['tool_key'] == build['tool_key']
        harness_path = ROOT / 'results/operation-map-python-tests-01/summary.json'
        harness = json.loads(harness_path.read_text())
        assert harness['status'] == 'passed' and harness['tests'] == 103
        harness_inputs = ROOT / harness['raw'] / 'inputs.json'
        assert sha(harness_inputs) == harness['inputs_sha256']
        assert all(sha(ROOT / p) == h for p, h in json.loads(harness_inputs.read_text()).items())
        reference_path = ROOT / 'results/current-runtime-boundaries-02/summary.json'
        baseline_path = ROOT / 'results/memory-operands-profile-01/summary.json'
        reference, baseline = [json.loads(p.read_text()) for p in [reference_path, baseline_path]]
        assert reference['status'] == baseline['status'] == 'passed'
        assert baseline['exact_per_pc_counts'] and baseline['exact_logical_counts_memory_and_entropy']
        raw, prior_raw = ROOT / reference['raw'], ROOT / baseline['raw']
        assert sha(raw / 'records.json') == reference['records_sha256']
        assert sha(prior_raw / 'records.json') == baseline['records_sha256']
        records = json.loads((raw / 'records.json').read_text())
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        entropy = json.loads(entropy_path.read_text()); assert entropy['status'] == 'passed'
        library = ROOT / entropy['library']; assert sha(library) == entropy['library_sha256']
        paths = [Path(__file__), Path(__file__).with_name('maps.py'), Path(__file__).with_name('QUALIFICATION.md'),
                 build_path, vm, proof_path, harness_path, harness_inputs, reference_path, baseline_path,
                 raw / 'records.json', prior_raw / 'records.json', entropy_path, library]
        paths += [ROOT / 'scripts' / p for p in ['workflow_io.py', 'compare_saved_runtime.py']]
        for item in reference['profiles']:
            index = item['index']
            old, = [r for r in baseline['comparisons'] if r['index'] == index]
            for field in ['artifact', 'catalog']:
                path = ROOT / item[field]; assert sha(path) == item[field + '_sha256']; paths.append(path)
            prior, = [r for r in records if r['index'] == index and r['mode'] == 'profile']
            tape = raw / f'{index}.tape'; assert sha(tape) == prior['tape_sha256']; paths.append(tape)
            for name, field in [(f'{index}-profile.json', 'profile_sha256'),
                                (f'{index}-code/code.bin', 'code_sha256'),
                                (f'{index}-code/map.json', 'code_map_sha256')]:
                path = prior_raw / name; assert sha(path) == old[field]; paths.append(path)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        work = ROOT / '.work' / args.run_id; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, expected_commands=3,
            tool_key=build['tool_key'], exact_adopted_code_comparison=True, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE='replay', RUST_INTERP_VM_STATS='1')
        rows, comparisons = [], []
        for item in reference['profiles']:
            require_space(ROOT, 8)
            index = item['index']; dump = work / f'{index}-code'; profile_path = work / f'{index}-profile.json'
            command = [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                '--jit-code-dump', str(dump), '--jit-operation-map', '--profile', str(profile_path),
                '--profile-test', item['name'], '--suite-catalog', str(ROOT / item['catalog']),
                '--instruction-limit', str(item['limits']['instructions']), '--allocation-limit', str(item['limits']['allocations']),
                str(ROOT / item['artifact'])]
            child, out, err = capture(command, cwd=ROOT, env=dict(env, RUST_INTERP_ENTROPY_TAPE=str(raw / f'{index}.tape')),
                receipt_path=work / 'active.json', receipt=dict(index=index))
            row = dict(index=index, pid=child.pid, command=command, returncode=child.returncode, stdout=out, stderr=err)
            rows.append(row); write(work / 'records.json', rows)
            assert child.returncode == 0 and out == '0\n', err
            selection, = [json.loads(line.split(': ', 1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            assert selection == item['selection']
            stats = {k: int(v) for k, v in re.findall(r'\b([a-z_]+)=(\d+)\b', err)}
            old, = [r for r in baseline['comparisons'] if r['index'] == index]
            for key in old['statistics']:
                if key.endswith('compile_ns'): continue
                assert stats[key] == old['statistics'][key], ('statistics mismatch', key)
            assert stats['jit_declined_functions'] == 0
            assert profile_path.stat().st_size <= 256 * 1024**2
            profile = json.loads(profile_path.read_text())
            exact_profile(profile, json.loads((prior_raw / f'{index}-profile.json').read_text()))
            assert sha(dump / 'code.bin') == old['code_sha256'], 'adopted generated bytes changed'
            assert (dump / 'operations.json').stat().st_size <= 256 * 1024**2
            operations, regions = [json.loads((dump / name).read_text()) for name in ['operations.json', 'map.json']]
            checked = validate(operations, regions, (dump / 'code.bin').read_bytes(), profile, child.pid)
            assert regions['profiled'] and regions['resumable_calls'] and regions['persistent_registers']
            assert regions['code_bytes'] == stats['jit_bytes']
            result = dict(index=index, spans=checked['spans'], mapped_pcs=checked['mapped_pcs'],
                assertions=checked['assertions'], static_words=checked['static_words'], exact_adopted_code=True,
                code_sha256=sha(dump / 'code.bin'), operation_map_sha256=sha(dump / 'operations.json'),
                map_sha256=sha(dump / 'map.json'), profile_sha256=sha(profile_path))
            comparisons.append(result); row.update(statistics=stats, selection=selection)
            write(work / 'records.json', rows); write(work / 'comparisons.json', comparisons)
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(index, 'exact code and profile; spans', checked['spans'], flush=True)
        out = ROOT / 'results' / args.run_id; out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=3, tool_key=build['tool_key'],
            vm_sha256=sha(vm), exact_adopted_code=True, exact_per_pc_profiles=True, comparisons=comparisons,
            performance_measurement=False, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json')))


if __name__ == '__main__': main()

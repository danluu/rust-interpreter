#!/usr/bin/env python3
"""Confirm interpreted boundaries on current, previously measured artifacts."""
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
from suite_reports import read_report, validate_report, validate_runtime_limits
from workflow_io import capture, require_space, write_json as write

KEY = '49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9'
CASES = [
    ('token', 'call-capacity-credit-edit-token-02', [
        'token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart',
        'token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex']),
    ('folded', 'call-capacity-credit-edit-folded-01', [
        'folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows']),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        controller = ROOT / '.work/experiments/host-mir-edits-01/status.json'
        terminal = json.loads(controller.read_text())
        assert terminal['owner'] == str(ROOT) and terminal['status'] == 'finished'
        assert terminal['returncode'] == 0
        build_path = ROOT / 'results/call-protocol-main-build-03/summary.json'
        exact_path = ROOT / 'results/call-protocol-main-qualification-01/summary.json'
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'
        build, exact, entropy = [json.loads(p.read_text()) for p in [build_path, exact_path, entropy_path]]
        assert build['status'] == exact['status'] == entropy['status'] == 'passed'
        assert build['tool_key'] == exact['tool_key'] == KEY
        assert exact['exact_instructions_memory_and_entropy']
        assert entropy['commands'] == 17 and entropy['expected_rejections'] == 10
        vm = ROOT / '.work/interpreter-tools' / KEY / 'rust-interp-vm'
        library = ROOT / entropy['library']
        assert sha(vm) == build['binaries']['rust-interp-vm']
        assert sha(library) == entropy['library_sha256']
        frozen_paths = [Path(__file__), Path(__file__).with_name('PLAN.md'), controller,
            build_path, exact_path, entropy_path, vm, library]
        frozen_paths += [ROOT / 'scripts' / p for p in ['compare_saved_runtime.py',
            'profile_vm_transitions.py', 'summarize_owned_sample.py', 'sample_owned_vm.py',
            'interpreter.py', 'suite_reports.py', 'workflow_io.py']]
        inputs = []
        for case, reference, names in CASES:
            proof_path = ROOT / 'results' / reference / 'summary.json'
            proof = json.loads(proof_path.read_text())
            assert proof['status'] == 'passed' and proof['commands'] == 154
            records_path = ROOT / proof['raw'] / 'records.json'
            assert sha(records_path) == proof['records_sha256']
            original, = [r for r in json.loads(records_path.read_text())
                if r['cycle'] == 0 and r['state'] == 0 and r['mode'] == 'baseline']
            assert original['launch']['tool_key'] == KEY
            artifact, catalog = [ROOT / original[k]['path'] for k in ['artifact', 'catalog']]
            assert all(sha(ROOT / original[k]['path']) == original[k]['sha256'] for k in ['artifact', 'catalog'])
            suite_path = ROOT / proof['raw'] / '0-0-baseline-suite.json'
            suite, _ = read_report(suite_path, original['suite_sha256'])
            validate_report(suite, [t['name'] for t in suite['tests']], 'prepared', True)
            frozen_paths += [proof_path, records_path, artifact, catalog, suite_path]
            entries = json.loads(catalog.read_text())['entries']
            for name in names:
                entry, = [e for e in entries if e['name'] == name]
                inputs.append(dict(case=case, reference=reference, name=name, function=entry['function'],
                    artifact=str(artifact.relative_to(ROOT)), artifact_sha256=sha(artifact),
                    catalog=str(catalog.relative_to(ROOT)), catalog_sha256=sha(catalog),
                    limits=suite['runtime_limits']))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in frozen_paths}
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), tool_key=KEY, frozen=frozen,
            inputs=inputs, expected_commands=6, performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_VM_STATS='1')
        records, summaries = [], []
        for index, item in enumerate(inputs):
            tape = work / f'{index}.tape'
            profile_path = work / f'{index}-profile.json'
            suite_path = work / f'{index}-control.json'
            subset = json.loads((ROOT / item['catalog']).read_text())
            subset['entries'] = [e for e in subset['entries'] if e['name'] == item['name']]
            assert len(subset['entries']) == 1
            subset_path = work / f'{index}-catalog.json'
            write(subset_path, subset)
            pair = {}
            for mode in ['control', 'profile']:
                require_space(ROOT, 8)
                command = [str(vm), '--engine', 'jit', '--jit-resumable-calls', '--jit-persistent-registers',
                    '--instruction-limit', str(item['limits']['instructions']),
                    '--allocation-limit', str(item['limits']['allocations'])]
                if mode == 'control':
                    command += ['--isolated-batch', 'fresh', '--suite-report', str(suite_path), '--suite-catalog', str(subset_path)]
                else:
                    command += ['--profile', str(profile_path), '--profile-test', item['name'], '--suite-catalog', str(ROOT / item['catalog'])]
                command.append(str(ROOT / item['artifact']))
                child_env = dict(env, RUST_INTERP_ENTROPY_MODE='record' if mode == 'control' else 'replay', RUST_INTERP_ENTROPY_TAPE=str(tape))
                child, out, err = capture(command, cwd=ROOT, env=child_env,
                    receipt_path=work / 'active.json', receipt=dict(index=index, case=item['case'], mode=mode))
                record = dict(index=index, mode=mode, command=command, pid=child.pid,
                    returncode=child.returncode, stdout=out, stderr=err)
                records.append(record)
                write(work / 'records.json', records)
                assert child.returncode == 0 and out == '0\n', err
                stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b', err)}
                assert all(k in stats for k in ['entropy_calls', 'entropy_bytes'])
                if mode == 'control':
                    suite, digest = read_report(suite_path)
                    validate_report(suite, [item['name']], 'fresh', True)
                    validate_runtime_limits(suite, item['limits']['instructions'], item['limits']['allocations'], required=True)
                    assert suite['runtime_limits'] == item['limits']
                    stats.update({k:suite['tests'][0][k] for k in ['instructions', 'peak_guest_memory', 'jit_declined_functions']})
                    record.update(suite_sha256=digest, subset_catalog_sha256=sha(subset_path))
                else:
                    selection, = [json.loads(line.removeprefix('rust-interp-profile-selection: '))
                        for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
                    assert all(selection[k] == item[k] for k in ['name', 'function', 'artifact_sha256', 'catalog_sha256'])
                    assert profile_path.stat().st_size <= 256 * 1024**2
                    attribution = counts(json.loads(profile_path.read_text()), stats)
                    for site in attribution['top_interpreted_sites']:
                        site['name'] = site['name'][:240]
                        site['operation_variant'] = site.pop('operation').split(' ', 1)[0]
                    summaries.append(dict(index=index, **item, profile_sha256=sha(profile_path),
                        selection=selection, statistics=stats, attribution=attribution))
                    record.update(profile_sha256=sha(profile_path), selection=selection)
                assert stats['jit_declined_functions'] == 0
                pair[mode] = {k:stats[k] for k in ['instructions', 'peak_guest_memory', 'entropy_calls', 'entropy_bytes']}
                record.update(statistics=stats, tape_sha256=sha(tape))
                write(work / 'records.json', records)
            assert pair['control'] == pair['profile'], item['name'] + ' changed exact execution'
            assert all(sha(ROOT / p) == h for p,h in frozen.items())
            write(work / 'profiles.json', summaries)
            print(index, item['name'], 'PASS', pair['profile']['instructions'], 'logical instructions', flush=True)
        result = ROOT / 'results' / args.run_id
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', commands=len(records), profiled_tests=len(summaries),
            tool_key=KEY, vm_sha256=sha(vm), exact_logical_counts_memory_and_entropy=True,
            jit_declines=0, performance_measurement=False, profiles=summaries, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            limitation='Instrumented logical counts on unchanged saved real artifacts. No elapsed-time attribution or hardware counts; no Cargo performance claim.'))


if __name__ == '__main__':
    main()

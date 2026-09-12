#!/usr/bin/env python3
"""Measure repeated lowering outputs in unchanged production-edit histories."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_cases import WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import source_states
from bench_e2e_workflow import guest_test_failure
from reuse_check import observation

REFERENCES = dict(token='fixed-frame-clear-library-token-02', folded='fixed-frame-clear-library-folded-01')


def compare(previous, current):
    old = {r['index']: r for r in previous['functions']}
    rows = current['functions']
    same = [r for r in rows if r['index'] in old and r['name'] == old[r['index']]['name']
            and r['lowered_sha256'] == old[r['index']]['lowered_sha256']]
    total = sum(r['prepare_seconds'] + r['lower_seconds'] for r in rows)
    repeated = sum(r['prepare_seconds'] + r['lower_seconds'] for r in same)
    return dict(functions=len(rows), repeated_lowered_functions=len(same),
        repeated_final_functions=sum(r['index'] in old and r['name'] == old[r['index']]['name']
            and r['final_sha256'] == old[r['index']]['final_sha256'] for r in rows),
        changed_index_or_name=sum(r['index'] not in old or r['name'] != old[r['index']]['name'] for r in rows),
        observed_function_seconds=total, repeated_output_seconds=repeated,
        repeated_output_cost_fraction=repeated / total if total else 0,
        repeated_prepare_seconds=sum(r['prepare_seconds'] for r in same),
        repeated_lower_seconds=sum(r['lower_seconds'] for r in same),
        semantics_proven=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=REFERENCES, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch('export-reuse-' + args.case + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        build_path = ROOT / 'results/export-reuse-build-01/summary.json'
        qualification_path = ROOT / 'results/export-reuse-fixtures-01/summary.json'
        build, qualification = [json.loads(p.read_text()) for p in [build_path, qualification_path]]
        assert build['status'] == qualification['status'] == 'passed'
        assert qualification['commands'] == 104 and qualification['all_artifact_hashes_identical']
        assert qualification['tool_key'] == build['tool_key']
        tool, key = installed_tools(build['tool_key'])
        reference_path = ROOT / 'results' / REFERENCES[args.case] / 'summary.json'
        reference = json.loads(reference_path.read_text())
        raw_reference = ROOT / reference['raw'] / 'records.json'
        original_rows = json.loads(raw_reference.read_text())
        references = {r['state']: r for r in original_rows if r['mode'] == 'baseline' and r['cycle'] == 0}
        assert set(references) == {0, -1, 1, 2, 3, 4, 5}
        case = WORKFLOW_VARIANTS[reference['project'], reference['workflow']]
        source = ROOT / '.work/sources/fre'
        marker = json.loads((source / '.rust-interp-owned.json').read_text())
        assert marker['owner'] == str(ROOT) and marker['revision'] == reference['revision']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == marker['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip()
        path = source / case['file']
        original = path.read_bytes()
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        # One fresh custom metadata cache, bounded by the prior token cache
        # inventory, plus all eight preserved artifacts and 20% growth margin.
        inventory = json.loads((ROOT / 'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json').read_text())
        cache_bytes = sum(g['bytes'] for g in inventory['manifest']['groups'])
        max_artifact = max((ROOT / r['artifacts'][0]['path']).stat().st_size for r in references.values())
        required = 8 * 1024**3 + (cache_bytes + 8 * max_artifact) * 12 // 10 + 128 * 1024**2
        free = shutil.disk_usage(ROOT).free
        write(work / 'admission.json', dict(required_free_bytes=required, observed_free_bytes=free,
              prior_custom_cache_bytes=cache_bytes, saved_artifacts=8, max_artifact_bytes=max_artifact))
        assert free >= required, 'insufficient diagnostic storage; source is unchanged'
        command = list(references[0]['calls'][0]['command'])
        command[1] = str(HERE / 'reuse_launcher.py')
        command[command.index('--tool-key') + 1] = key
        command[command.index('--cache-namespace') + 1] = args.run_id
        paths = [Path(__file__), HERE / 'reuse_launcher.py', HERE / 'reuse_check.py', HERE / 'REUSE.md',
                 build_path, qualification_path, reference_path, raw_reference]
        paths += [ROOT / 'scripts' / p for p in ['interpreter.py', 'workflow_io.py', 'workflow_cases.py', 'workflow_measurements.py', 'std_mir.py']]
        paths += [ROOT / r['artifacts'][0]['path'] for r in references.values()]
        paths += [tool / name for name in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, source_commit=build['source_commit'], tool_key=key,
              source_revision=marker['revision'], command=command, performance_measurement=False,
              states=[0, -1, 1, 2, 3, 4, 5, 'restored']))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=references[0]['calls'][0]['rustflags'],
                   CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
        records, censuses, transitions = [], [], []
        def execute(state):
            require_space(ROOT, 8)
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(state=state))
            label = str(state)
            (work / (label + '.stdout')).write_text(stdout)
            (work / (label + '.stderr')).write_text(stderr)
            row = dict(state=state, pid=child.pid, returncode=child.returncode, source_sha256=sha(path))
            records.append(row)
            write(work / 'records.json', records)
            assert (child.returncode == 0) == (state != -1)
            assert guest_test_failure(stderr) if state == -1 else stdout.strip() == '0'
            launches = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(launches) == 1
            launch = launches[0]
            assert launch['tool_key'] == key and launch['jit_resumable_calls'] and launch['jit_persistent_registers']
            artifact = Path(launch['artifact_path'])
            saved = work / (label + '.rbc')
            shutil.copy2(artifact, saved)
            row.update(artifact_sha256=sha(saved), artifact=str(saved.relative_to(ROOT)), launch=launch)
            report, scopes = observation(stderr, saved)
            write(work / (label + '.census.json'), report)
            row.update(census_sha256=sha(work / (label + '.census.json')), timings=scopes)
            expected = references[0 if state == 'restored' else state]
            row['matches_retained_artifact'] = sha(saved) == expected['artifacts'][0]['sha256']
            write(work / 'records.json', records)
            assert row['source_sha256'] == expected['source_sha256']
            assert row['matches_retained_artifact'], 'artifact differs; preserve evidence and investigate'
            if censuses:
                transitions.append(dict(before_state=records[-2]['state'], state=state, **compare(censuses[-1], report)))
                write(work / 'transitions.json', transitions)
            censuses.append(report)
            assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
            print('PASS', args.case, state, report['observed_functions'], 'functions; original assertions and artifact match', flush=True)
        with SourceEdit(path, original) as edit:
            for state in source_states(original.decode(), case, 1, ['native', 'baseline', 'candidate'], True):
                edit.replace(state['source'])
                execute(state['state'])
        assert path.read_bytes() == original
        execute('restored')
        edited = [r for r in transitions if type(r['state']) is int and r['state'] > 0]
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', performance_measurement=False, tool_key=key,
              source_commit=build['source_commit'], project=reference['project'], workflow=reference['workflow'],
              revision=reference['revision'], commands=len(records), edited_states=5, wrong_edit_rejected=True,
              source_restored=True, restored_source_rebuilt=True, original_tests_unchanged=True,
              all_artifact_hashes_identical=True, transitions=transitions,
              median_repeated_output_seconds=statistics.median(r['repeated_output_seconds'] for r in edited),
              median_observed_function_seconds=statistics.median(r['observed_function_seconds'] for r in edited),
              median_repeated_output_cost_fraction=statistics.median(r['repeated_output_cost_fraction'] for r in edited),
              frozen=frozen, raw=str(work.relative_to(ROOT)), records_sha256=sha(work / 'records.json'),
              scope='Cost-weighted repeated outputs only. No semantic cache-key proof, cache hit rate, speedup or cold-build claim.'))


if __name__ == '__main__':
    main()

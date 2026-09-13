"""Recompute the inherited fixed gates from complete observations-off runs."""
import argparse
import json
import math
from pathlib import Path
import statistics

from run_local_export_adoption import B, ROOT, FROZEN, BASELINE, CANDIDATE, STD_KEY
from run_local_export_adoption import bind, read, require, sha, verify, write_new


def controller(frozen, phase, proofs):
    path = B / ('local-export-adoption-' + phase + '-controller.json')
    result = read(path)
    require(result['status'] == 'complete' and result['frozen_sha256'] == sha(FROZEN),
            'complete frozen controller required')
    planned = frozen['commands'][phase]
    require(result['planned_commands'] == planned and len(result['calls']) == len(planned),
            'all planned histories/verifiers required')
    previous = result['started_at']
    for actual, expected in zip(result['calls'], planned):
        require({k: actual[k] for k in ['label', 'kind', 'command']} == expected
                and actual['returncode'] == 0 and actual['status'] == 'complete'
                and previous <= actual['started_at'] <= actual['finished_at'],
                'controller command/interval failed')
        previous = actual['finished_at']
        bind(proofs, B / (actual['label'] + '-controller.log'), actual['log_sha256'])
    cases = [case for case in frozen['cases'] if case['phase'] == phase]
    require(len(result['admissions']) == len(cases), 'missing admission')
    for admission, case in zip(result['admissions'], cases):
        require(admission['label'] == case['run_id']
                and admission['minimum_gib'] == case['minimum_admission_gib']
                and admission['free_bytes'] >= case['minimum_admission_gib'] * 2**30
                and admission['lock_wait_started'] <= admission['time'] <= admission['lock_released_at'],
                'fixed admission did not pass')
    bind(proofs, path)
    return cases


def stats(ratios):
    require(ratios and all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in ratios),
            'invalid paired ratio')
    return dict(ratios=ratios, median=statistics.median(ratios), min=min(ratios), max=max(ratios))


def history(frozen, case, proofs):
    folder = ROOT / 'results' / case['run_id']
    report, checked = read(folder / 'summary.json'), read(folder / 'verification.json')
    for key in ['measurement_controls_verified', 'explicit_controls_verified',
                'paired_bytecode_identical', 'build_to_ready_metrics_verified',
                'restored_original_build_and_execution_verified']:
        require(checked[key] is True, 'independent verifier failed: ' + key)
    require(type(checked['exact_artifact_hashes_verified']) is int
            and checked['exact_artifact_hashes_verified'] == case['artifacts'],
            'independent verifier artifact count differs')
    for key in ['project', 'revision', 'workflow', 'cycles', 'tests', 'initial_mode_order', 'case_sha256']:
        require(report[key] == case[key], 'case differs: ' + key)
    require(len(report['edits']) == case['edit_count'] and report['test_source_unchanged'] is True,
            'original production edit/test history differs')
    settings = dict(batch=True, compare_isolated_batches=False, cargo_timings=False, vary_selection=False,
                    build_tool_opt_level=0, build_jobs=18, custom_build_jobs={'baseline': 18, 'candidate': 18},
                    instruction_limit=100000000000, allocation_limit=150000, inline_leaves=True,
                    baseline_inline_leaves=True, trap_unsupported_calls=True, run_try_callbacks=True,
                    guest_mir_opt_level=3, guest_mir_inline_scale=8, minimum_free_gib=1,
                    baseline_guest_mir_opt_level=None)
    for key, expected in settings.items():
        require(report[key] == expected, 'fixed common setting differs: ' + key)
    metrics, check_floor = report['build_metrics'], report['check_floor']
    require(isinstance(metrics, dict)
            and metrics['boundary'] == 'launcher start to validated artifact ready, before VM invocation'
            and metrics['cpu_accounting'] == 'launcher self plus waited-for child CPU at the pre-VM boundary; user plus system'
            and set(metrics['median_seconds']) == set(metrics['median_cpu_seconds']) == {'baseline', 'candidate'},
            'readiness metric definition differs')
    require(isinstance(check_floor, dict)
            and check_floor['interpretation'] == 'Independent library-test Cargo-check control; executes no tests, including the wrong runtime edit; not a strict lower bound or subtractive attribution'
            and check_floor['timing_position'] == 'after each primary mode triplet; separate target/cache history; no Cargo timing-report generation',
            'independent checking control definition differs')
    require(report['native_control'] == dict(profile='repository', jobs=18, test_threads='1',
                    rustflags=[], isolation='ordinary libtest batch'), 'native profile/jobs/threading differs')
    require(report['std_mir']['key'] == STD_KEY and report['std_mir']['metadata_bytes'] == 112958025,
            'std-MIR identity differs')
    require(report['cache_workspaces'] == case['cache_workspaces']
            and report['cache_namespaces'] == {mode: case['run_id'] + ':' + mode for mode in ['baseline', 'candidate']},
            'fresh per-mode cache mapping differs')
    for name, digest in report['scripts_sha256'].items():
        bind(proofs, ROOT / name, digest)
    for mode in ['baseline', 'candidate']:
        bundle, tools = frozen['bundles'][mode], report['tool_builds'][mode]
        require(tools['tool_key'] == bundle['tool_key'] and tools['engine'] == 'jit'
                and tools['vm_sha256'] == bundle['binaries']['rust-interp-vm']
                and tools['exporter_sha256'] == bundle['binaries']['rust-interp-mir-export']
                and tools['jit_resumable_calls'] and tools['jit_persistent_registers']
                and not tools['jit_native_calls'] and not tools['jit_native_call_stubs'], 'selected tools differ')
    raw = ROOT / report['raw']
    require(raw == ROOT / '.work/runs' / case['run_id'], 'wrong raw directory')
    records, checks = read(raw / 'records.json'), read(raw / 'check-records.json')
    require(check_floor['samples'] == [{k: v for k, v in check.items()
                                      if k not in ['stdout', 'stderr', 'command']} for check in checks],
            'checking samples differ from the retained raw controls')
    require(len(records) == case['primary_commands'] and sum(len(r['calls']) for r in records) == len(records)
            and len(checks) == case['check_commands']
            and sum(len(r.get('artifacts', [])) for r in records) == case['artifacts'], 'raw control count differs')
    require(checked['commands'] == case['primary_commands'] and checked['edited_pairs'] == case['edited_pairs']
            and checked['check_commands'] == case['check_commands'], 'verifier count differs')
    transitions = read(raw / 'source-transitions.json')
    require(transitions == report['source_transitions'] and len(transitions) == case['check_commands'],
            'source transition archive differs')
    for transition in transitions:
        state = transition['state'] if transition['state'] != -2 else 0
        require(transition['source_sha256'] == case['source_states'][str(state)], 'source state differs from original protocol')
    edited = {}
    for record in records:
        require(record['tests'] == case['tests'], 'original tests were not retained')
        for artifact in record.get('artifacts', []):
            path = ROOT / artifact['path']
            require(path.is_relative_to(raw) and path.stat().st_size == artifact['bytes'], 'artifact path/extent differs')
            bind(proofs, path, artifact['sha256'])
        call = record['calls'][0]
        require(not any(prefix in call['stderr'] for prefix in [
                'rust-interp-function-costs: ', 'rust-interp-export-timings: ']),
                'compiler observations are enabled in an adoption sample')
        if record['mode'] == 'native':
            continue
        messages = [line.removeprefix('rust-interp-launch: ') for line in call['stderr'].splitlines()
                    if line.startswith('rust-interp-launch: ')]
        require(len(messages) == 1 and json.loads(messages[0]) == call['launch'], 'launch receipt differs from raw stderr')
        launch, mode = call['launch'], record['mode']
        bundle = frozen['bundles'][mode]
        require(launch['tool_key'] == bundle['tool_key'] and launch['engine'] == 'jit'
                and launch['compiler_wrapper']['sha256'] == bundle['binaries']['rust-interp-rustc-wrapper']
                and launch['workspace_path'] == case['cache_workspaces'][mode], 'launch tool/cache binding differs')
        require(call['command'].count('--entry') == len(case['tests'])
                and [call['command'][i + 1] for i, value in enumerate(call['command']) if value == '--entry'] == case['tests'],
                'exact entry list differs')
        if record['phase'] != 'edit':
            continue
        require(call['returncode'] == 0, 'correct production edit did not pass')
        values = dict(seconds=launch['build_to_ready_seconds'],
                      cpu_seconds=launch['build_to_ready_cpu']['total_seconds'])
        require(all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in values.values()),
                'invalid readiness metrics')
        key = record['cycle'], record['state'], mode
        require(key not in edited, 'duplicate edited sample')
        edited[key] = dict(source=record['source_sha256'], **values)
    pairs = report['comparison']['pairs']
    expected_keys = {(cycle, state) for cycle in range(case['cycles']) for state in range(1, case['edit_count'] + 1)}
    require(len(pairs) == case['edited_pairs'] and len(edited) == 2 * len(pairs)
            and {(p['cycle'], p['state']) for p in pairs} == expected_keys, 'all exact edited pairs required')
    result = dict(run=case['run_id'], project=case['project'], group=case['group'], pairs=len(pairs))
    for suffix, label in [('seconds', 'wall'), ('cpu_seconds', 'cpu')]:
        ratios = []
        for pair in pairs:
            values = {}
            for mode in ['baseline', 'candidate']:
                row = edited[(pair['cycle'], pair['state'], mode)]
                require(row['source'] == pair['source_sha256'] and math.isclose(
                        row[suffix], pair[mode + '_build_to_ready_' + suffix], rel_tol=1e-12, abs_tol=1e-12),
                        'summary pair differs from raw launch metric')
                values[mode] = row[suffix]
            ratios.append(values['candidate'] / values['baseline'])
        result[label] = stats(ratios)
    result['regression_guard_pass'] = all(result[k]['median'] <= 1.05 for k in ['wall', 'cpu'])
    for path in [folder / 'summary.json', folder / 'verification.json', raw / 'records.json',
                 raw / 'check-records.json', raw / 'source-transitions.json']:
        bind(proofs, path)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['screen', 'confirmation'])
    args = parser.parse_args()
    frozen = read(FROZEN)
    proofs = dict(frozen['proofs'])
    verify(proofs)
    bind(proofs, FROZEN)
    cases = controller(frozen, args.phase, proofs)
    rows = [history(frozen, case, proofs) for case in cases]
    if args.phase == 'screen':
        require(len(rows) == 6, 'six complete screen histories required')
        aggregate = {}
        for group in ['token', 'pgrust']:
            selected = [r for r in rows if r['group'] == group]
            require(len(selected) == 3 and sum(r['pairs'] for r in selected) == 15, 'all 15 pairs/project required')
            aggregate[group] = {key: stats([v for r in selected for v in r[key]['ratios']]) for key in ['wall', 'cpu']}
        passed = (aggregate['token']['wall']['median'] <= .95 and aggregate['token']['cpu']['median'] < 1
                  and all(aggregate['pgrust'][k]['median'] <= 1.05 for k in ['wall', 'cpu'])
                  and all(r['regression_guard_pass'] for r in rows))
        result = dict(screen_pass=passed, aggregate=aggregate, histories=rows,
                      decision='proceed to fixed confirmations' if passed else 'park; fixed 5% build gate missed')
    else:
        screen_path = B / 'local-export-adoption-screen-assessment.json'
        screen = read(screen_path)
        require(screen['screen_pass'] is True and screen['all_planned_runs_included'] is True, 'complete screen PASS required')
        verify(screen['proofs'])
        bind(proofs, screen_path)
        require(len(rows) == 2 and [r['pairs'] for r in rows] == [15, 3], 'complete Ruff/Nu confirmations required')
        passed = all(r['regression_guard_pass'] for r in rows)
        result = dict(confirmations_pass=passed, complete_screen_pass=True, cases=rows,
                      decision='qualified for production review' if passed else 'park; public confirmation guard failed')
    result.update(baseline_tool_key=BASELINE, candidate_tool_key=CANDIDATE,
                  all_planned_runs_included=True, aa_noise_subtracted=False,
                  diagnostic_samples_included=False, compiler_observations=False, proofs=proofs)
    write_new(B / ('local-export-adoption-' + args.phase + '-assessment.json'), result)
    print(json.dumps({k: v for k, v in result.items() if k != 'proofs'}, indent=2))


if __name__ == '__main__':
    main()

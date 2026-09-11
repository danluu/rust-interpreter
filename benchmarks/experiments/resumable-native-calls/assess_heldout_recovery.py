#!/usr/bin/env python3
"""Verify complete held-out cases across a preserved failure and one fresh retry."""
import fcntl
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools
from tool_source_index import index
from verify_repeated_workflow import verify, require

ORIGINAL = 'resumable-bulk-heldout-01'
RETRY = 'resumable-bulk-heldout-retry-02'
FAILURE = 'results/resumable-bulk-heldout-failure-01/summary.json'
LABELS = {'pgrust', 'nushell', 'rg-aot', 'forward-anchored-tls',
          'pgrust-sha1-inline8', 'ruff', 'nushell-type-relations'}


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def archived_inputs(plan, commit):
    commit = subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT, text=True).strip()
    for path, expected in plan['frozen'].items():
        contents = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
        require(hashlib.sha256(contents).hexdigest() == expected, 'archived harness differs: ' + path)
    return dict(commit=commit, inputs=plan['frozen'])


def main():
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    old_path = '.work/corpus-runs/' + ORIGINAL + '/status.json'
    old = read(old_path)
    recovery = read(FAILURE)
    require(recovery['status'] == 'incomplete: ENOSPC' and recovery['source_restored'] and
            recovery['incomplete_workflow'] == 'nushell-type-relations', 'missing failure/restoration evidence')
    for path, evidence in recovery['evidence'].items():
        require(digest(path) == evidence['sha256'], 'original failed-run evidence changed')
        require(digest(str(Path(FAILURE).parent / evidence['snapshot'])) == evidence['sha256'], 'failure snapshot changed')
    require(old['status'] == 'running' and len(old['completed']) == 6,
            'expected preserved stale receipt with six completed cases')
    retry_status = read('.work/corpus-runs/' + RETRY + '/status.json')
    supervisor = read('.work/experiments/' + RETRY + '/status.json')
    require(retry_status['status'] == 'finished' and supervisor['status'] == 'finished' and
            supervisor['returncode'] == 0, 'retry not successfully terminal')
    rejected = read('.work/experiments/resumable-bulk-heldout-retry-01/status.json')
    require(rejected['status'] == 'finished' and rejected['returncode'] == 1, 'initial rejected retry not preserved')
    corpus = read('results/' + RETRY + '/summary.json')
    require(corpus['workflows'] == retry_status['completed'] and
            [r['label'] for r in corpus['workflows']] == ['nushell-type-relations'], 'retry case differs')
    plans = {ORIGINAL: read('.work/corpus-runs/' + ORIGINAL + '/plan.json'), RETRY: corpus['plan']}
    archived = {ORIGINAL: archived_inputs(plans[ORIGINAL], 'edf0c2b'),
                RETRY: archived_inputs(plans[RETRY], 'e4a9613')}
    options = plans[RETRY]['options']
    def controls(opts):
        return {k: v for k, v in opts.items() if k not in ['run_id', 'only']}
    require(controls(plans[ORIGINAL]['options']) == controls(options), 'retry changed benchmark controls')
    # Derive exact identities from the previously qualified original comparison.
    primary = read('results/resumable-bulk-e2e-02/gate-evaluation.json')
    baseline = primary['baseline_tool_key']
    build = index('001065a')
    require(options['baseline_tool_key'] == baseline and options['candidate_tool_key'] == build['tool_key'], 'tool identity differs')
    require(options['cycles'] == 3 and options['candidate_jit_resumable_calls'] and
            options['candidate_jit_persistent_registers'] and not options['candidate_jit_native_calls'] and
            not options['candidate_jit_native_call_stubs'], 'runtime settings differ')
    require(options['jobs'] == 4 and options['native_jobs'] == 18 and options['native_profile'] == 'o0-incremental' and
            options['native_test_threads'] == 'default' and options['native_rustflag'] == [], 'native controls differ')
    binaries = {}
    for key in [baseline, build['tool_key']]:
        directory, _ = installed_tools(key)
        binaries[key] = json.loads((directory / 'ready.json').read_text())
    pins = {}
    for project, config in read('benchmarks/corpus.json')['projects'].items():
        source = ROOT / '.work/sources' / project
        marker = json.loads((source / '.rust-interp-owned.json').read_text())
        require(marker['owner'] == str(ROOT) and marker['revision'] == config['revision'], 'ownership differs')
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == config['revision'], 'source pin differs')
        require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(), 'source not restored')
        pins[project] = config['revision']
    rows = old['completed'] + corpus['workflows']
    require(len(rows) == 7 and {r['label'] for r in rows} == LABELS, 'incomplete held-out set')
    totals = dict(primary_commands=0, check_commands=0, edited_pairs=0, artifacts=0)
    evaluated = []
    for row in rows:
        require(digest(row['report']) == row['report_sha256'], 'workflow report changed')
        report = read(row['report'])
        run = RETRY if row['label'] == 'nushell-type-relations' else ORIGINAL
        for path, expected in report['scripts_sha256'].items():
            contents = subprocess.check_output(['git', 'show', archived[run]['commit'] + ':' + path], cwd=ROOT)
            require(hashlib.sha256(contents).hexdigest() == expected, 'measured script differs from archived harness')
        case = next(c for c in plans[run]['cases'] if c['label'] == row['label'])
        require(digest(case['reference_report']) == case['reference_report_sha256'] and
                report['case_sha256'] == read(case['reference_report'])['case_sha256'], 'original workload changed')
        require(report['native_control'] == dict(profile='o0-incremental', jobs=18, test_threads='default', rustflags=[]) and
                report['build_jobs'] == 4, 'measured controls differ')
        verification = verify(report)
        require(verification == read(str(Path(row['report']).with_name('verification.json'))), 'workflow verification differs')
        comparison = report['comparison']
        require(comparison['baseline_tool_key'] == baseline and comparison['candidate_tool_key'] == build['tool_key'] and
                comparison['identical_bytecode_required'], 'comparison identities differ')
        for mode, setting in report['tool_builds'].items():
            require(mode in ['baseline', 'candidate'] and setting['tool_key'] ==
                    (baseline if mode == 'baseline' else build['tool_key']), 'executed mode/tool mapping differs')
            require(setting['engine'] == 'jit' and setting['jit_resumable_calls'] == (mode == 'candidate') and
                    setting['jit_persistent_registers'] == (mode == 'candidate') and not setting['jit_native_calls'] and
                    not setting['jit_native_call_stubs'], 'executed runtime flags differ')
            for name, field in [('rust-interp-vm', 'vm_sha256'), ('rust-interp-mir-export', 'exporter_sha256')]:
                require(setting[field] == binaries[setting['tool_key']][name], 'executed binary differs')
        for total, field in [('primary_commands', 'commands'), ('check_commands', 'check_commands'),
                             ('edited_pairs', 'edited_pairs'), ('artifacts', 'exact_artifact_hashes_verified')]:
            totals[total] += verification[field]
        pairs = comparison['pairs']
        ratio = median(p['candidate_seconds'] / p['baseline_seconds'] for p in pairs)
        cpu = median(p['candidate_cpu_seconds'] / p['baseline_cpu_seconds'] for p in pairs)
        evaluated.append(dict(workflow=row['label'], report=row['report'], report_sha256=row['report_sha256'],
            median_paired_wall_ratio=ratio, median_paired_cpu_ratio=cpu, wall_limit=1.05, wall_check_passed=ratio <= 1.05,
            median_seconds=report['median_seconds'], median_cpu_seconds=report['median_cpu_seconds'],
            cross_cycle_bytecode_identical=verification['cross_cycle_bytecode_identical'],
            stages={m: {s: median(p['stage_seconds'][m][s] for p in pairs) for s in ['execution_seconds', 'cargo_seconds']}
                    for m in ['baseline', 'candidate']}))
    require(totals == dict(primary_commands=441, check_commands=147, edited_pairs=105, artifacts=294), 'incomplete command/artifact totals')
    result = dict(status='seven complete cases verified across two run histories',
        original_run_status='incomplete: ENOSPC; unchanged', retry_run=RETRY, failure_report=FAILURE,
        failure_sha256=digest(FAILURE), partial_failed_case_excluded_from_complete_totals=dict(primary_records=12, check_records=3),
        source_commit=build['commit'], candidate_tool_key=build['tool_key'], baseline_tool_key=baseline,
        archived_harnesses=archived, source_pins_restored=pins, installed_binaries=binaries,
        counts=totals, workflows=evaluated, held_out_wall_checks_passed=all(r['wall_check_passed'] for r in evaluated),
        wall_regressions_above_5_percent=[r['workflow'] for r in evaluated if r['median_paired_wall_ratio'] > 1.05],
        cpu_regressions_above_5_percent=[r['workflow'] for r in evaluated if r['median_paired_cpu_ratio'] > 1.05],
        original_primary_gates_unchanged=True, retained=False,
        note='Five percent is an engineering threshold, not a confidence interval. Original token gates remain failed. IO harness differs across histories, not within a paired case.',
        assessor_sha256=digest(str(Path(__file__).relative_to(ROOT))))
    out = ROOT / 'results/resumable-bulk-heldout-recovery-01'
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Completed held-out cases after an interrupted run', '',
        'Six original cases plus one fresh Nushell retry verify 588 commands, 105 edited pairs and 294 artifacts.',
        'The original run remains incomplete; its partial records and failure are preserved separately.', '',
        '| Workflow | Paired wall change | Paired CPU change | Above wall limit? |', '| --- | ---: | ---: | --- |']
    for row in evaluated:
        lines.append(f"| {row['workflow']} | {(row['median_paired_wall_ratio'] - 1) * 100:+.2f}% | {(row['median_paired_cpu_ratio'] - 1) * 100:+.2f}% | {'no' if row['wall_check_passed'] else 'yes'} |")
    lines += ['', 'All ratios compare fixed candidate 78e60cdd with original b2 within each edit.',
        'Both original token primary gates remain failed. This assessment does not retain the runtime.',
        'See [complete provenance and stages](summary.json) and [preserved failure](../resumable-bulk-heldout-failure-01/assessment.md).', '']
    (out / 'assessment.md').write_text('\n'.join(lines))
    print(json.dumps(dict(counts=totals, wall_regressions=result['wall_regressions_above_5_percent'])))


if __name__ == '__main__':
    main()

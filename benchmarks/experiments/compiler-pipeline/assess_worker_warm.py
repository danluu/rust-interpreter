#!/usr/bin/env python3
"""Reverify a fixed fifteen-cycle worker comparison and its raw paired timings."""
import argparse
import fcntl
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require, verify
from workflow_io import write_json

# Installed identities, not a request to rebuild tools for this assessment.
TOOL = '78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d'
VM = '60b00d7de39977e6512e8335d449e5eac84c48ff95819dc2feae6ed8220a859c'
EXPORTER = '64d7102e21ae5017564076d40781c1c9f5e05cf62bff7abefb6f8519fd0fb317'
STD = 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
PINS = {'pgrust': '38d2517d3e09168a8fe222837730d435238ff358',
        'nushell': '9d3157963241cf89447119d34d6e887859f5e7e8'}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(name):
    work = ROOT / '.work/experiments' / name
    status, plan = read(work / 'status.json'), read(work / 'plan.json')
    require(status['status'] == 'finished' and status['returncode'] == 0 and
            status['owner'] == status['cwd'] == plan['owner'] == str(ROOT) and
            status['command'] == plan['command'] and
            status['plan_sha256'] == sha(work / 'plan.json') and
            status['log_sha256'] == sha(work / 'command.log'), 'experiment receipt differs')
    return plan['command']


def checked_primary(project):
    name = f'worker-count-{project}-repeated-01'
    qualification = f'worker-count-{project}-qualification-' + ('02' if project == 'pgrust' else '01')
    command = receipt(qualification)
    command[command.index('--run-id') + 1] = name
    command[command.index('--cycles') + 1] = '15'
    if '--initial-mode-order' in command:
        command[command.index('--initial-mode-order') + 1] = 'native,baseline,candidate'
    else:
        command += ['--initial-mode-order', 'native,baseline,candidate']
    require(receipt(name) == command, 'primary command differs from qualified recipe')
    out = ROOT / 'results' / name
    report = read(out / 'summary.json')
    require(report['project'] == project and report['revision'] == PINS[project] and
            report['cycles'] == 15 and len(report['edits']) == 1 and
            report['raw'] == '.work/runs/' + name, 'wrong primary case')
    require(report['custom_build_jobs'] == {'baseline': 4, 'candidate': 18} and
            report['native_control'] == dict(profile='o0-incremental', jobs=18,
                                            test_threads='default', rustflags=[]), 'worker controls differ')
    settings = dict(engine='jit', tool_key=TOOL, jit_persistent_registers=False,
        jit_resumable_calls=False, inline_leaves=True, jit_native_calls=False,
        jit_native_call_stubs=False, trap_unsupported_calls=False,
        run_try_callbacks=False, guest_rustflags=[], vm_sha256=VM, exporter_sha256=EXPORTER)
    require(report['tool_builds'] == dict(baseline=settings, candidate=settings), 'installed tools/options differ')
    binaries = {'rust-interp-vm': VM, 'rust-interp-mir-export': EXPORTER}
    installed = ROOT / '.work/interpreter-tools' / TOOL
    require(read(installed / 'ready.json') == binaries and
            all(sha(installed / binary) == digest for binary, digest in binaries.items()),
            'installed binary integrity differs')
    require((report['std_mir']['key'] if report['std_mir'] else None) ==
            (STD if project == 'nushell' else None), 'std-MIR differs')
    require(len(report['scripts_sha256']) == 11 and
            all(sha(ROOT / p) == h for p, h in report['scripts_sha256'].items()), 'frozen inputs differ')
    verified = verify(report)
    require(verified == read(out / 'verification.json') and verified['commands'] == 135 and
            verified['check_commands'] == 45 and verified['exact_artifact_hashes_verified'] == 90,
            'primary workflow verification differs')
    for state in [0, -1, 1]:
        orders = [o['modes'] for o in report['mode_orders'] if o['state'] == state]
        for mode in ['native', 'baseline', 'candidate']:
            require([sum(order.index(mode) == p for order in orders) for p in range(3)] == [5, 5, 5],
                    'primary mode positions are not balanced')
    raw = ROOT / report['raw']
    rows = read(raw / 'records.json')
    traces = 0
    for row in rows:
        if row['mode'] != 'native':
            for call in row['calls']:
                require(call['launch']['compiler_wrapper'] ==
                        dict(name='rust-interp-mir-export', sha256=EXPORTER), 'wrapper trace differs')
                traces += 1
    require(traces == 90, 'unexpected wrapper count')
    relative = read(raw / 'case.json')['case']['file']
    source = ROOT / '.work/sources' / project
    original = subprocess.check_output(['git', '-C', str(source), 'show', PINS[project] + ':' + relative])
    require((source / relative).read_bytes() == original and subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == PINS[project],
        'pinned source not restored')
    pairs = report['comparison']['pairs']
    require(len(pairs) == 15 and [(p['cycle'], p['state']) for p in pairs] ==
            [(c, 1) for c in range(15)], 'paired timing identities differ')
    for pair in pairs:
        for mode in ['native', 'baseline', 'candidate']:
            selected = [r for r in rows if (r['cycle'], r['state'], r['mode']) ==
                        (pair['cycle'], pair['state'], mode)]
            require(len(selected) == 1, 'pair lacks unique raw row')
            row = selected[0]
            require(pair['source_sha256'] == row['source_sha256'] and
                    pair[mode + '_seconds'] == row['seconds'] and
                    pair[mode + '_cpu_seconds'] == row['cpu_seconds'], 'paired timing differs from raw row')
    for mode in ['native', 'baseline', 'candidate']:
        edited = [r for r in rows if r['mode'] == mode and r['phase'] == 'edit']
        require(report['median_seconds'][mode] == median(r['seconds'] for r in edited) and
                report['median_cpu_seconds'][mode] == median(r['cpu_seconds'] for r in edited),
                'reported median differs from raw rows')
    ratios = {}
    for label, suffix in [('wall', 'seconds'), ('cpu', 'cpu_seconds')]:
        values = [Fraction(str(p['candidate_' + suffix])) / Fraction(str(p['baseline_' + suffix])) for p in pairs]
        middle = median(values)
        ratios[label] = dict(minimum=float(min(values)), median=float(middle), maximum=float(max(values)),
            exact_median_fraction=str(middle), per_cycle=[float(v) for v in values])
    result = dict(status='verified', run=name, project=project, pairs=15, ratios=ratios,
        median_seconds=report['median_seconds'], median_cpu_seconds=report['median_cpu_seconds'],
        verification=verified, frozen_input_hashes=11, compiler_wrapper_traces=traces,
        source_revision=PINS[project], source_file=relative, source_restored=True,
        source_sha256=hashlib.sha256(original).hexdigest(), tool_builds=report['tool_builds'],
        custom_build_jobs=report['custom_build_jobs'], native_control=report['native_control'],
        report_sha256=sha(out / 'summary.json'), records_sha256=sha(raw / 'records.json'),
        supervisor_status_sha256=sha(ROOT / '.work/experiments' / name / 'status.json'),
        warm_wall_guard_passed=Fraction(ratios['wall']['exact_median_fraction']) <= Fraction(105, 100),
        cpu_guard_passed=Fraction(ratios['cpu']['exact_median_fraction']) <= Fraction(110, 100),
        retained=False, assessor_sha256=sha(Path(__file__)))
    return out, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, choices=PINS)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out, result = checked_primary(args.project)
        if not args.check_only:
            path = out / 'worker-verification.json'
            require(not path.exists(), 'worker assessment already exists')
            write_json(path, result)
        print(json.dumps({k: result[k] for k in ['run', 'ratios', 'warm_wall_guard_passed', 'cpu_guard_passed']}))


if __name__ == '__main__':
    main()

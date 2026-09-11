#!/usr/bin/env python3
"""Verify a completed primary or held-out corpus against the original controls."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import verify, require
from interpreter import installed_tools
from tool_source_index import index

TARGETS = {'folded-literal-trie': 0.9, 'token-phrase': 0.8}
HELD_OUT = {'pgrust', 'nushell', 'rg-aot', 'forward-anchored-tls',
            'pgrust-sha1-inline8', 'ruff', 'nushell-type-relations'}
BASELINE = 'b2aa6efe746cf00d40703af478c750c49c2d07eb11508c2b28d08122f17b15cc'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--held-out', action='store_true', help='verify the seven other workflows and flag paired wall regressions above 5 percent')
    parser.add_argument('--check-existing', action='store_true', help='recompute and compare existing receipts without overwriting them')
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ('.', '..'), 'invalid run ID')
    status = read(ROOT / '.work/corpus-runs' / args.run_id / 'status.json')
    supervisor = read(ROOT / '.work/experiments' / args.run_id / 'status.json')
    require(status['status'] == 'finished' and supervisor['status'] == 'finished' and supervisor['returncode'] == 0, 'corpus still active or failed')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    out = ROOT / 'results' / args.run_id
    corpus = read(out / 'summary.json')
    options = corpus['plan']['options']
    targets = {name: 1.05 for name in HELD_OUT} if args.held_out else TARGETS
    require(options['baseline_tool_key'] == BASELINE, 'original baseline changed')
    native = options.get('candidate_jit_native_calls', False)
    resumable = options.get('candidate_jit_resumable_calls', False)
    require(options['cycles'] == 3 and native != resumable, 'unexpected corpus options')
    require(not (resumable and options.get('candidate_jit_native_call_stubs', False)), 'incompatible native options')
    require({r['label'] for r in corpus['workflows']} == set(targets), 'missing or unexpected workload')
    require(all(sha(ROOT / p) == h for p, h in corpus['plan']['frozen'].items()), 'frozen scripts changed')
    build = index(args.source_commit)
    require(build['tool_key'] == options['candidate_tool_key'] and build['binaries'], 'source/tool mismatch')
    pins, binaries = {}, {}
    for name, config in read(ROOT / 'benchmarks/corpus.json')['projects'].items():
        source = ROOT / '.work/sources' / name
        marker = read(source / '.rust-interp-owned.json')
        require(marker['owner'] == str(ROOT) and marker['revision'] == config['revision'], 'source ownership mismatch')
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        changes = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip()
        require(revision == config['revision'] and not changes, 'source pin/restoration failed: ' + name)
        pins[name] = dict(revision=revision, tracked_sources_restored=True)
    for key in [BASELINE, build['tool_key']]:
        directory, _ = installed_tools(key)
        binaries[key] = read(directory / 'ready.json')
    counts = dict(primary_commands=0, check_commands=0, edited_pairs=0, artifacts=0)
    evaluated, evidence = [], {}
    for row in corpus['workflows']:
        path = ROOT / row['report']
        require(sha(path) == row['report_sha256'], 'report hash changed')
        report = read(path)
        verified = verify(report)
        require(verified == read(path.with_name('verification.json')), 'verification receipt mismatch')
        require(report['candidate_jit_native_calls'] == native and report.get('candidate_jit_native_call_stubs', False) == options.get('candidate_jit_native_call_stubs', False), 'candidate native flags differ')
        require(report.get('candidate_jit_resumable_calls', False) == resumable, 'candidate resumable flag differs')
        require(report.get('candidate_jit_persistent_registers', False) == options.get('candidate_jit_persistent_registers', False), 'candidate persistent-register flag differs')
        for mode, settings in report['tool_builds'].items():
            expected = mode == 'candidate'
            require(settings['jit_native_calls'] == (expected and native) and settings.get('jit_native_call_stubs', False) == (expected and options.get('candidate_jit_native_call_stubs', False)), 'measured tool mode differs')
            require(settings.get('jit_resumable_calls', False) == (expected and resumable), 'measured resumable mode differs')
            require(settings.get('jit_persistent_registers', False) == (expected and options.get('candidate_jit_persistent_registers', False)), 'measured register mode differs')
            for name, field in [('rust-interp-vm', 'vm_sha256'), ('rust-interp-mir-export', 'exporter_sha256')]:
                require(settings[field] == binaries[settings['tool_key']][name], 'measured binary differs')
        counts['primary_commands'] += verified['commands']
        counts['check_commands'] += verified['check_commands']
        counts['edited_pairs'] += verified['edited_pairs']
        counts['artifacts'] += verified['exact_artifact_hashes_verified']
        pairs = report['comparison']['pairs']
        ratio = median(p['candidate_seconds'] / p['baseline_seconds'] for p in pairs)
        cpu_ratio = median(p['candidate_cpu_seconds'] / p['baseline_cpu_seconds'] for p in pairs)
        target = targets[row['label']]
        evaluated.append(dict(workload=row['label'], medians=report['median_seconds'], cpu_medians=report['median_cpu_seconds'],
            median_paired_ratio=ratio, median_paired_cpu_ratio=cpu_ratio, target_max_ratio=target,
            median_paired_difference_seconds=median(p['difference_seconds'] for p in pairs),
            median_paired_cpu_difference_seconds=median(p['cpu_difference_seconds'] for p in pairs),
            passed=ratio <= target and (args.held_out or cpu_ratio < 1),
            stages={m: {s: median(p['stage_seconds'][m][s] for p in pairs) for s in ['execution_seconds', 'cargo_seconds']} for m in ['baseline', 'candidate']}))
        evidence[row['report']] = sha(path)
        evidence[str(path.with_name('verification.json').relative_to(ROOT))] = sha(path.with_name('verification.json'))
    cases = len(targets)
    require(counts == dict(primary_commands=63 * cases, check_commands=21 * cases,
                          edited_pairs=15 * cases, artifacts=42 * cases), 'corpus command count changed')
    checks = dict(frozen_scripts_unchanged=True, candidate_option_verified=True, source_pins=pins,
        counts=counts, installed_binaries_verified=binaries, evidence=evidence)
    gates = dict(source_commit=build['commit'], tool_key=build['tool_key'], baseline_tool_key=BASELINE,
        evaluated=evaluated, retained=False, primary_gates_passed=all(r['passed'] for r in evaluated),
        reason='Primary gates alone cannot authorize retention; held-out workflows and broader execution qualification remain required',
        held_out_workflows_run=False, broader_native_tls_fre_qualification_run=False)
    if args.held_out:
        gates = dict(source_commit=build['commit'], tool_key=build['tool_key'], baseline_tool_key=BASELINE,
            evaluated=evaluated, retained=False, held_out_workflows_run=True,
            held_out_wall_checks_passed=all(r['passed'] for r in evaluated),
            wall_regressions_above_5_percent=[r['workload'] for r in evaluated if r['median_paired_ratio'] > 1.05],
            cpu_regressions_above_5_percent=[r['workload'] for r in evaluated if r['median_paired_cpu_ratio'] > 1.05],
            reason='Characterization of seven held-out workflows. Primary gates remain separate and unchanged; no default retention follows from passing these checks. The 5 percent threshold is an engineering target, not a confidence interval.')
    for name, value in [('final-verification.json', checks), ('gate-evaluation.json', gates)]:
        path = out / name
        if args.check_existing:
            require(read(path) == value, 'existing gate evidence differs: ' + name)
            continue
        require(not path.exists(), 'refusing to overwrite previous gate evidence')
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(counts=counts, evaluated=evaluated)))


if __name__ == '__main__':
    main()

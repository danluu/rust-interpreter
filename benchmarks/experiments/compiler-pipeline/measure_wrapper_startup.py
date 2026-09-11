#!/usr/bin/env python3
"""Measure ordinary-rustc routing overhead; this is not a build benchmark."""
import argparse
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
from statistics import median
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools, TOOLCHAIN
from workflow_io import capture, require_space, write_json
from workflow_measurements import child_usage, child_cpu_since


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path, help='verified paired public workflow report')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    report_path = args.report.resolve(strict=True)
    require(report_path.is_relative_to(ROOT / 'results'), 'report outside results')
    report = json.loads(report_path.read_text())
    require(report['project'] in ['pgrust', 'nushell', 'ruff', 'fre'], 'public projects only')
    verification_path = report_path.with_name('verification.json')
    verification = json.loads(verification_path.read_text())
    require(verification['measurement_controls_verified'] is True, 'unverified report')
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in
        [Path(__file__), ROOT / 'scripts/interpreter.py', ROOT / 'scripts/workflow_io.py',
         ROOT / 'scripts/workflow_measurements.py', report_path, verification_path]}
    # Verify immutable executable hashes before any timing. No sources are built.
    tool_paths = {}
    identities = {}
    for mode in ['baseline', 'candidate']:
        key = report['comparison'][mode + '_tool_key']
        directory, _ = installed_tools(key)
        manifest = json.loads((directory / 'ready.json').read_text())
        name = 'rust-interp-rustc-wrapper' if 'rust-interp-rustc-wrapper' in manifest else 'rust-interp-mir-export'
        tool_paths[mode] = directory / name
        identities[mode] = dict(tool_key=key, wrapper_name=name, wrapper_sha256=sha(tool_paths[mode]),
                               exporter_sha256=manifest['rust-interp-mir-export'])
    out = ROOT / 'results' / args.run_id
    raw = ROOT / '.work/runs' / args.run_id
    require(not out.exists() and not raw.exists(), 'run already exists')
    require_space(ROOT / '.work', 8)
    raw.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith('RUST_INTERP_')}
    preparations = []

    def prepare(command):
        child, stdout, stderr = capture(command, cwd=ROOT, env=env,
            receipt_path=raw / 'active-command.json', receipt=dict(phase='preparation'))
        preparations.append(dict(command=command, returncode=child.returncode,
                                 stdout=stdout, stderr=stderr))
        write_json(raw / 'preparation.json', preparations)
        require(child.returncode == 0, 'compiler preparation failed')
        return stdout

    rustc = Path(prepare(['rustup', 'which', '--toolchain', TOOLCHAIN, 'rustc']).strip()).resolve(strict=True)
    require(rustc.stem == 'rustc', 'wrapper detection requires a rustc executable')
    expected = prepare([str(rustc), '-vV'])
    commands = {'direct': [str(rustc), '-vV']}
    commands.update({m: [str(p), str(rustc), '-vV'] for m, p in tool_paths.items()})
    permutations = list(itertools.permutations(commands))
    rows = []
    # Five repetitions of all six permutations: each path visits each position
    # ten times. Every observation is retained, including the first one.
    for cycle in range(30):
        for mode in permutations[cycle % len(permutations)]:
            before = child_usage()
            start = time.perf_counter()
            child, stdout, stderr = capture(commands[mode], cwd=ROOT, env=env,
                receipt_path=raw / 'active-command.json',
                receipt=dict(phase='version-probe', cycle=cycle, mode=mode))
            elapsed = time.perf_counter() - start
            cpu = child_cpu_since(before)
            rows.append(dict(cycle=cycle, mode=mode, command=commands[mode], seconds=elapsed,
                cpu=cpu, pid=child.pid, returncode=child.returncode, stdout=stdout, stderr=stderr,
                load=os.getloadavg()))
            write_json(raw / 'records.json', rows)
            require(child.returncode == 0 and stdout == expected and not stderr,
                    'routed compiler version differs or routing failed')
    require(all(sha(ROOT / p) == digest for p, digest in source_hashes.items()), 'diagnostic input changed')
    for identity in identities.values():
        installed_tools(identity['tool_key'])
    summary = dict(schema_version=1, status='passed',
        input_report=str(report_path.relative_to(ROOT)), input_sha256=sha(report_path),
        verification_sha256=sha(verification_path), tools=identities,
        compiler=dict(path=str(rustc), sha256=sha(rustc), version=expected),
        raw=str(raw.relative_to(ROOT)), commands=len(rows), preparation_commands=len(preparations),
        cycles=30, original_project_compiled=False, guest_executed=False,
        median_seconds={m: median(r['seconds'] for r in rows if r['mode'] == m) for m in commands},
        paired_overhead={},
        source_hashes=source_hashes,
        interpretation='Version probes isolate a small routing/startup diagnostic after prior compiler work. They do not compile source, exercise std-MIR argument routing, measure cold-loader behavior, or establish removable time in real builds. Wall times include the common active-command receipt publication; CPU covers each waited-for child tree. No sample is filtered.')
    for mode in ['baseline', 'candidate']:
        pairs = []
        for cycle in range(30):
            group = {r['mode']: r for r in rows if r['cycle'] == cycle}
            pairs.append(dict(cycle=cycle,
                seconds=group[mode]['seconds'] - group['direct']['seconds'],
                cpu_seconds=group[mode]['cpu']['total_seconds'] - group['direct']['cpu']['total_seconds']))
        summary['paired_overhead'][mode] = dict(pairs=pairs,
            median_seconds=median(p['seconds'] for p in pairs),
            median_cpu_seconds=median(p['cpu_seconds'] for p in pairs))
    out.mkdir()
    write_json(out / 'summary.json', summary)
    print(json.dumps(dict(medians=summary['median_seconds'], overhead={m:
        summary['paired_overhead'][m]['median_seconds'] for m in ['baseline', 'candidate']})))


if __name__ == '__main__':
    main()

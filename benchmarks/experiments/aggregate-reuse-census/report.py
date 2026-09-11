#!/usr/bin/env python3
"""Build the typed profile join and report weighted additional array-reuse scope."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

from build import ROOT, EXPERIMENT, environment, sha, write
from verify_repeated_workflow import require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--collection-run', required=True)
    args = parser.parse_args()
    for value in [args.run_id, args.collection_run]:
        require(Path(value).name == value and value not in ('.', '..'), 'invalid run ID')
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    receipt = work / 'status.json'
    status = dict(owner=str(ROOT), status='waiting for benchmark lock', pid=os.getpid(),
        parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time())
    write(receipt, status)
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + 600
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                status.update(status='failed', error='benchmark lock wait expired', finished_at=time.time())
                write(receipt, status)
                raise
            time.sleep(1)
    try:
        collection = ROOT / '.work' / args.collection_run
        require(json.loads((collection / 'status.json').read_text())['status'] == 'finished', 'collection not terminal')
        report = json.loads((collection / 'summary.json').read_text())
        require(report['status'] == 'passed' and report['source_unchanged'], 'collection failed')
        frozen = dict(report['frozen'])
        paths = [Path(__file__), EXPERIMENT / 'Cargo.toml', EXPERIMENT / 'weights.rs', collection / 'summary.json']
        for case in report['cases']:
            for field in ['artifact', 'profile', 'inventory']:
                path = ROOT / case[field]
                require(sha(path) == case[field + '_sha256'], 'collection input changed')
                paths.append(path)
        frozen.update({str(p.relative_to(ROOT)): sha(p) for p in paths})
        for name, digest in report['binaries'].items():
            path = ROOT / '.work/interpreter-tools' / report['tool_key'] / name
            frozen[str(path.relative_to(ROOT))] = digest
        parent_vm = ROOT / '.work/interpreter-tools' / report['parent_tool_key'] / 'rust-interp-vm'
        frozen[str(parent_vm.relative_to(ROOT))] = report['binaries']['rust-interp-vm']

        def verify():
            require(all(sha(ROOT / p) == h for p, h in frozen.items()), 'frozen census input changed')

        env = environment()
        records = []

        def invoke(label, command):
            verify()
            with (work / (label + '.stdout')).open('x') as out, (work / (label + '.stderr')).open('x') as err:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
                status.update(status='running', label=label, child_pid=child.pid, command=command, child_started_at=time.time())
                write(receipt, status)
                code = child.wait()
            records.append(dict(label=label, pid=child.pid, parent_pid=os.getpid(), cwd=str(ROOT), command=command,
                returncode=code, started_at=status['child_started_at'], finished_at=time.time(),
                files={str((work / (label + suffix)).relative_to(ROOT)): sha(work / (label + suffix)) for suffix in ['.stdout', '.stderr']}))
            write(work / 'commands.json', records)
            require(code == 0, label + ' failed')
            verify()

        manifest = EXPERIMENT / 'Cargo.toml'
        lockfile = EXPERIMENT / 'Cargo.lock'
        if not lockfile.exists():
            invoke('lockfile', ['cargo', '+nightly-2026-09-08', 'generate-lockfile', '--offline', '--manifest-path', str(manifest)])
        frozen[str(lockfile.relative_to(ROOT))] = sha(lockfile)
        archived = work / 'source'
        archived.mkdir()
        for name in ['Cargo.toml', 'Cargo.lock', 'weights.rs', 'report.py', 'build.py']:
            (archived / name).write_bytes((EXPERIMENT / name).read_bytes())
        target = ROOT / '.work/diagnostic-builds' / args.run_id
        require(not target.exists(), 'census build target already exists')
        write(work / 'plan.json', dict(collection_run=args.collection_run, frozen=frozen,
            source_archive=str(archived.relative_to(ROOT)), target=str(target.relative_to(ROOT)),
            performance_measurement=False))
        for action in ['test', 'build']:
            invoke(action, ['cargo', '+nightly-2026-09-08', action, '--release', '--locked', '--offline', '--jobs', '2',
                '--manifest-path', str(manifest), '--target-dir', str(target)])
        tests = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', (work / 'test.stdout').read_text())
        require(sum(int(n) for n, _ in tests) == 3 and all(f == '0' for _, f in tests), 'missing weight-tool checks')
        binary = target / 'release/aggregate-reuse-weights'
        summaries = []
        for case in report['cases']:
            invoke(case['label'], [str(binary), *[str(ROOT / case[field]) for field in ['artifact', 'profile', 'inventory']]])
            path = work / (case['label'] + '.stdout')
            result = json.loads(path.read_text())
            require(result['instructions'] == case['statistics']['instructions'], 'profile instruction accounting differs')
            require(result['inventory_ids_checked'] == case['inventories'], 'inventory ID coverage differs')
            totals = result['totals']
            percentage = 100 * totals['additional_bytes_saved'] / totals['direct_frame_bytes']
            row = dict(label=case['label'], artifact_sha256=case['artifact_sha256'], profile_sha256=case['profile_sha256'],
                inventory_sha256=case['inventory_sha256'], instructions=result['instructions'], totals=totals,
                additional_frame_byte_percentage=percentage, array_exclusion_bytes=result['array_exclusion_bytes'],
                physical_layout_class_bytes=result['physical_layout_class_bytes'],
                indirect_calls_without_target_attribution=result['indirect_calls_without_target_attribution'],
                inventory_ids_checked=result['inventory_ids_checked'],
                top_saved_callees=sorted(result['callees'], key=lambda r: -r['weighted_additional_bytes_saved'])[:15],
                top_frame_callees=sorted(result['callees'], key=lambda r: -r['frame_bytes'])[:15],
                raw_census=str(path.relative_to(ROOT)), raw_census_sha256=sha(path))
            summaries.append(row)
            print(json.dumps(dict(label=case['label'], totals=totals, additional_frame_byte_percentage=percentage)), flush=True)
        verify()
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        summary = dict(status='passed', observer_tool_key=report['tool_key'], parent_tool_key=report['parent_tool_key'],
            cases=summaries, typed_weight_tests=3, source_unchanged=True, production_change=False,
            performance_measurement=False, binary_sha256=sha(binary), frozen=frozen, commands=records,
            collection_report='results/' + args.collection_run + '/summary.json',
            limitations='Additional hypothetical local extents only, weighted by verified matching direct calls. No runtime transformation or speedup prediction. Indirect targets, entry/TLS frames and alignment padding excluded.')
        write(work / 'summary.json', summary)
        write(out / 'summary.json', summary)
        status.update(status='finished', returncode=0, finished_at=time.time())
        write(receipt, status)
    except BaseException as error:
        status.update(status='failed', error=repr(error), finished_at=time.time())
        write(receipt, status)
        raise


if __name__ == '__main__':
    main()

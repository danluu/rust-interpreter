#!/usr/bin/env python3
"""Freshly collect and replay a discovered test list in bounded, recorded batches.

This is body execution coverage, not a full libtest or performance measurement.
Each collection and replay child takes the benchmark lock. The coordinator
releases its lock before launching either child to avoid waiting on itself.
No compiler cache or artifact is deleted. A failed child needs an explicit audit;
resume accepts only fully committed batches followed by an untouched next batch.
"""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from interpreter import ROOT, installed_tools, validate_audit_pack

OPTIONS = ['jit_native_calls', 'jit_native_call_stubs', 'jit_persistent_registers', 'jit_resumable_calls']


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def guard():
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    parser.add_argument('--project', choices=['pgrust', 'fre', 'nushell', 'ruff'], required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--entries', type=Path, required=True)
    parser.add_argument('--discovery-record', type=Path, required=True)
    parser.add_argument('--previous-results', type=Path, help='compare every outcome and available artifact hash')
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--stop-after-batches', type=int, help='stop at a completed batch boundary; --resume continues')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--instruction-limit', type=int, default=100_000_000_000)
    parser.add_argument('--allocation-limit', type=int, default=150_000)
    parser.add_argument('--std-mir', action='store_true')
    parser.add_argument('--inline-leaves', action='store_true')
    parser.add_argument('--trap-unsupported-calls', action='store_true')
    parser.add_argument('--run-try-callbacks', action='store_true')
    parser.add_argument('--guest-mir-opt-level', type=int, choices=range(4))
    parser.add_argument('--guest-mir-inline-scale', type=int, choices=[1, 2, 4, 8])
    for name in OPTIONS:
        parser.add_argument('--' + name.replace('_', '-'), action='store_true')
    args = parser.parse_args()
    if not __debug__ or sys.flags.optimize:
        parser.error('coverage qualification requires enabled Python assertions')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('invalid run ID')
    if not 1 <= args.batch_size <= 64:
        parser.error('batch size must be between 1 and 64')
    if args.stop_after_batches is not None and args.stop_after_batches <= 0:
        parser.error('stop-after-batches must be positive')
    if not 0 < args.instruction_limit < 2**64 or not 0 <= args.allocation_limit < 2**64:
        parser.error('instruction/allocation limits must fit unsigned 64-bit counts')
    if args.jit_native_call_stubs and not args.jit_native_calls:
        parser.error('native Call stubs require native calls')
    if args.jit_resumable_calls and (args.jit_native_calls or args.jit_native_call_stubs):
        parser.error('resumable calls exclude native tree/stub calls')
    if args.guest_mir_inline_scale is not None and args.guest_mir_opt_level != 3:
        parser.error('MIR inline scaling requires MIR level 3')
    if args.run_try_callbacks and not args.trap_unsupported_calls:
        parser.error('try callbacks require explicit unsupported-call trapping')

    lock = guard()
    tool, key = installed_tools(args.tool_key)
    binaries = read(tool / 'ready.json')
    names = sorted(read(args.entries))
    require(names and all(isinstance(n, str) and n for n in names) and len(names) == len(set(names)),
            'invalid or duplicate discovered entries')
    discovery = read(args.discovery_record)
    listed = sorted(line.removesuffix(': test') for line in discovery['stdout'].splitlines() if line.endswith(': test'))
    require(discovery['returncode'] == 0 and listed == names, 'entries differ from native discovery')
    previous = {} if args.previous_results is None else {r['entry']: r for r in read(args.previous_results)}
    if args.previous_results is not None:
        require(sorted(previous) == names and len(read(args.previous_results)) == len(names), 'previous coverage differs')
    source = ROOT / '.work/sources' / args.project
    revision = read(ROOT / 'benchmarks/corpus.json')['projects'][args.project]['revision']
    owner = read(source / '.rust-interp-owned.json')
    require(owner['owner'] == str(ROOT) and owner['revision'] == revision, 'source ownership mismatch')

    def source_ok():
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == revision,
                'source revision changed')
        require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
                'original sources or tests changed')

    options = {name: getattr(args, name) for name in OPTIONS}
    runtime_flags = ['--' + name.replace('_', '-') for name, enabled in options.items() if enabled]
    export_options = {name: getattr(args, name) for name in
                      ['std_mir', 'inline_leaves', 'trap_unsupported_calls', 'run_try_callbacks']}
    export_flags = ['--' + name.replace('_', '-') for name, enabled in export_options.items() if enabled]
    for name in ['guest_mir_opt_level', 'guest_mir_inline_scale']:
        if getattr(args, name) is not None:
            export_flags += ['--' + name.replace('_', '-'), str(getattr(args, name))]
    work = ROOT / '.work' / args.run_id
    config = dict(tool_key=key, binaries=binaries, project=args.project, package=args.package, revision=revision,
                  runtime_options=options, export_flags=export_flags, names=names, batch_size=args.batch_size,
                  instruction_limit=args.instruction_limit, allocation_limit=args.allocation_limit,
                  entries=str(args.entries.resolve()), discovery_record=str(args.discovery_record.resolve()),
                  previous_results=None if args.previous_results is None else str(args.previous_results.resolve()))
    paths = [Path(__file__).resolve(), ROOT / 'scripts/audit_test_lowering.py',
             ROOT / 'scripts/survey_audit_execution.py', ROOT / 'scripts/interpreter.py', ROOT / 'scripts/std_mir.py',
             ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml', ROOT / 'benchmarks/corpus.json',
             tool / 'ready.json', tool / 'rust-interp-vm', tool / 'rust-interp-mir-export',
             args.entries.resolve(), args.discovery_record.resolve(), *sorted((ROOT / 'crates').rglob('*.rs'))]
    paths += sorted((ROOT / 'crates').glob('*/Cargo.toml'))
    if args.previous_results is not None:
        paths.append(args.previous_results.resolve())
    frozen = {str(p): sha(p) for p in paths}
    if args.resume:
        plan = read(work / 'plan.json')
        require(plan['config'] == config and plan['frozen'] == frozen, 'resume inputs changed')
    else:
        work.mkdir(exist_ok=False)
        (work / 'batches').mkdir()
        (work / 'selections').mkdir()
        write(work / 'plan.json', dict(config=config, frozen=frozen, fresh_exports=True,
                                      performance_measurement=False, created_at=time.time()))
    coordinator = (work / 'coordinator.lock').open('a')
    fcntl.flock(coordinator, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def freeze():
        require(all(sha(Path(p)) == digest for p, digest in frozen.items()), 'frozen coverage input changed')
        source_ok()

    batches = [names[i:i + args.batch_size] for i in range(0, len(names), args.batch_size)]
    committed = sorted((work / 'batches').glob('*.json'))
    require([p.name for p in committed] == [f'{i:03}.json' for i in range(len(committed))], 'noncontiguous completed batches')
    records = [read(p) for p in committed]
    rows = []
    for i, record in enumerate(records):
        require(record['index'] == i, 'batch index changed')
        for path, digest in record['evidence'].items():
            require(sha(ROOT / path) == digest, 'completed batch evidence changed')
        require([r['entry'] for r in record['rows']] == batches[i], 'completed batch selection changed')
        rows += record['rows']
    require(len(records) < len(batches), 'coverage already complete')
    status = dict(status='starting', pid=os.getpid(), parent_pid=os.getppid(), cwd=str(ROOT), started_at=time.time(),
                  completed_batches=len(records))
    write(work / 'status.json', status)
    freeze()

    def run(label, command):
        freeze()
        command = list(map(str, command))
        with (work / (label + '.log')).open('x') as output:
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
            receipt = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(), cwd=str(ROOT),
                           started_at=time.time(), status='running')
            write(work / 'active-command.json', receipt)
            print('START', label, child.pid, flush=True)
            code = child.wait()
        receipt.update(status='finished', returncode=code, finished_at=time.time())
        write(work / 'active-command.json', receipt)
        with (work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(receipt) + '\n')
        require(code == 0, 'coverage child failed; inspect ' + label + '.log before any retry')
        freeze()

    try:
        stop = min(len(batches), args.stop_after_batches or len(batches))
        require(stop > len(records), 'stop-after-batches does not advance completed coverage')
        for index in range(len(records), stop):
            require(shutil.disk_usage(ROOT).free >= 3 * 1024**3, 'less than 3 GiB free before batch; no cleanup attempted')
            label = f'{index:03}'
            collect_id = args.run_id + '-collect-' + label
            replay_id = args.run_id + '-replay-' + label
            for run_id in [collect_id, replay_id]:
                require(not (ROOT / 'results' / run_id).exists() and not (ROOT / '.work/runs' / run_id).exists(),
                        'uncommitted child output exists; inspect previous failure before retry')
            selection = work / 'selections' / (label + '.json')
            require(not selection.exists(), 'uncommitted selection exists; inspect previous failure')
            write(selection, batches[index])
            status.update(status='running', batch=index)
            write(work / 'status.json', status)
            lock.close()
            run('collect-' + label, [sys.executable, ROOT / 'scripts/audit_test_lowering.py',
                '--project', args.project, '--package', args.package, '--tool-key', key,
                '--entries', args.entries.resolve(), '--discovery-record', args.discovery_record.resolve(),
                '--selection', selection, '--retain-audit-bodies', *export_flags, '--run-id', collect_id])
            collect_path = ROOT / 'results' / collect_id / 'summary.json'
            collection = read(collect_path)
            report_path = ROOT / collection['raw'] / 'report.json'
            report = read(report_path)
            require(collection['tool_key'] == key and collection['revision'] == revision and
                    collection['strict_frontend'] is True and collection['executed'] is False and
                    collection['sampled'] == len(batches[index]) and collection['discovered'] == len(names),
                    'fresh collection identity changed')
            require([r['entry'] for r in report['entries']] == batches[index], 'fresh collection selection changed')
            for name, enabled in export_options.items():
                require(collection[name] is enabled, 'fresh collection option changed: ' + name)
            replay = [sys.executable, ROOT / 'scripts/survey_audit_execution.py', '--collection', collect_path,
                      '--vm-tool-key', key, '--instruction-limit', args.instruction_limit,
                      '--allocation-limit', args.allocation_limit, *runtime_flags, '--run-id', replay_id]
            if records:
                replay += ['--native-control-provenance', ROOT / records[0]['native_control']]
            run('replay-' + label, replay)
            lock = guard()
            freeze()
            replay_path = ROOT / 'results' / replay_id / 'summary.json'
            survey = read(replay_path)
            raw = ROOT / survey['raw']
            current = read(raw / 'results.json')
            require([r['entry'] for r in current] == batches[index], 'fresh replay selection changed')
            require(survey['tool_key'] == survey['collection_tool_key'] == key and survey['runtime_options'] == options,
                    'replay tool or runtime options changed')
            require(survey['instruction_limit'] == args.instruction_limit and survey['allocation_limit'] == args.allocation_limit,
                    'replay limits changed')
            control = str((raw / 'native-provenance.json').relative_to(ROOT)) if not records else records[0]['native_control']
            if not records:
                require(survey['reused_native_control'] is None, 'first native control was not freshly built')
            else:
                require(survey['reused_native_control']['path'] == control and
                        survey['native_binary_sha256'] == records[0]['native_binary_sha256'], 'native control changed')
            for row in current:
                if 'jit' not in row:
                    continue
                cmd = row['jit']['command']
                require(cmd[:3] == [str(tool / 'rust-interp-vm'), '--engine', 'jit'], 'captured VM identity changed')
                for name, enabled in options.items():
                    require(cmd.count('--' + name.replace('_', '-')) == int(enabled), 'captured VM options changed')
                for name, value in [('instruction-limit', args.instruction_limit), ('allocation-limit', args.allocation_limit)]:
                    require(cmd.count('--' + name) == 1 and cmd[cmd.index('--' + name) + 1] == str(value), 'captured VM limit changed')
                if row['status'] == 'passed':
                    require('jit_entries' in row['jit_stats'], 'missing successful JIT statistics')
            validate_audit_pack(report, Path(report['artifacts']['directory']).parent)
            evidence_paths = [collect_path, report_path, replay_path, raw / 'results.json', raw / 'commands.jsonl',
                              ROOT / control, selection]
            record = dict(index=index, collection=str(collect_path.relative_to(ROOT)), replay=str(replay_path.relative_to(ROOT)),
                          evidence={str(p.relative_to(ROOT)): sha(p) for p in evidence_paths}, rows=current,
                          native_control=control, native_binary_sha256=survey['native_binary_sha256'],
                          artifact_bytes=collection['retained_artifacts']['bytes'])
            write(work / 'batches' / (label + '.json'), record)
            records.append(record)
            rows += current
            write(work / 'results.json', rows)
            counts = dict(Counter(r['status'] for r in rows))
            status.update(status='between batches', completed_batches=len(records), counts=counts)
            write(work / 'status.json', status)
            print('DONE', label, counts, flush=True)
        complete = len(records) == len(batches)
        failures = [r['entry'] for r in rows if r['status'] not in ['passed', 'ignored']]
        changes = [dict(entry=r['entry'], previous=previous[r['entry']]['status'], current=r['status'])
                   for r in rows if previous and previous[r['entry']]['status'] != r['status']]
        hashed = [r for r in rows if previous and 'artifact_sha256' in r and 'artifact_sha256' in previous[r['entry']]]
        passed = [r for r in rows if r['status'] == 'passed']
        calls = sum(r['jit_stats'].get('jit_resumable_calls', 0) for r in passed)
        returns = sum(r['jit_stats'].get('jit_resumable_returns', 0) for r in passed)
        if complete and options['jit_resumable_calls']:
            require(calls > 0 and returns > 0, 'resumable transitions did not execute')
        summary = dict(status=('passed' if not failures and not changes else 'failed') if complete else 'incomplete',
            tool_key=key, tool_binaries=binaries, project=args.project, package=args.package, revision=revision,
            runtime_options=options, export_flags=export_flags, allocation_limit=args.allocation_limit,
            instruction_limit=args.instruction_limit, selected=len(rows), discovered=len(names), batches=len(records),
            counts=dict(Counter(r['status'] for r in rows)), failures=failures, outcome_changes=changes,
            compared_artifacts=len(hashed), changed_artifacts=sum(r['artifact_sha256'] != previous[r['entry']]['artifact_sha256'] for r in hashed),
            native_builds=1, fresh_native_controls=sum('native' in r and r['native']['returncode'] == 0 for r in rows),
            native_binary_sha256=records[0]['native_binary_sha256'], native_control=records[0]['native_control'],
            resumable_calls=calls, resumable_returns=returns,
            maximum_generated_bytes=max((r['jit_stats']['jit_bytes'] for r in passed), default=0),
            executions_with_declines=sum(r['jit_stats']['jit_declined_functions'] > 0 for r in passed),
            fresh_exports=True, strict_frontend=True, original_sources_and_tests_unchanged=True,
            raw=str(work.relative_to(ROOT)), records=[{k: v for k, v in r.items() if k != 'rows'} for r in records],
            frozen_inputs=frozen, performance_measurement=False,
            scope='Fresh ordinary body replay with native processes. Ignored, lowering-blocked and unsupported bodies are separate. No full libtest, unwinding, FFI or thread support claim.')
        freeze()
        write(work / 'summary.json', summary)
        if complete:
            out = ROOT / 'results' / args.run_id
            out.mkdir(exist_ok=False)
            write(out / 'summary.json', summary)
            lines = [f'# Fresh body execution: {args.project} / {args.package}', '',
                f"Status: {summary['status']}. Recollected {len(names)} bodies in {len(records)} batches with tool `{key}`.", '',
                '| Outcome | Bodies |', '| --- | ---: |',
                *[f'| {name} | {count} |' for name, count in sorted(summary['counts'].items())], '',
                f"The native control was built once and ran in {summary['fresh_native_controls']} fresh test processes. Original sources, tests and strict frontend checks were preserved.", '',
                'Export options: `' + ' '.join(export_flags) + '`. Runtime options: `' + ' '.join(runtime_flags) + '`.',
                f'Per-body limits: {args.instruction_limit:,} instructions and {args.allocation_limit:,} live allocations.', '',
                f"Successful runs made {calls:,} resumable Calls and {returns:,} Returns. Maximum generated code was {summary['maximum_generated_bytes']:,} bytes; {summary['executions_with_declines']} successful executions declined functions.", '',
                f"Compared {len(hashed)} available artifact hashes with previous coverage; {summary['changed_artifacts']} changed. Outcome changes: {len(changes)}. Individual results and exact commands remain in `{summary['raw']}`.", '',
                summary['scope'], 'This is compatibility evidence, not an edit-to-test performance measurement.']
            (out / 'assessment.md').write_text('\n'.join(lines) + '\n')
        status.update(status='finished' if complete else 'paused at completed batch boundary',
                      returncode=int(complete and summary['status'] != 'passed'), finished_at=time.time())
        write(work / 'status.json', status)
        raise SystemExit(status['returncode'])
    except Exception as error:
        status.update(status='failed', error=str(error), finished_at=time.time())
        write(work / 'status.json', status)
        raise


if __name__ == '__main__':
    main()

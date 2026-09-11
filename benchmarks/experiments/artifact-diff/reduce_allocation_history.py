#!/usr/bin/env python3
"""Compare a reduced API/literal history with Cargo incremental reuse on and off."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from allocation_trace import selected_trace
from inspect_allocation_origins import inspect
from interpreter import installed_tools, require_export_option, TOOLCHAIN
from qualify_trace_launcher import TOOL, lines
from std_mir import checked_std_mir
from verify_repeated_workflow import require
from workflow_io import SourceEdit, capture, require_space, write_json

SEEDS = [0, 7, 2**64 - 1, 42, 43, 40]
PANIC_SEEDS = {42, 43, 40}
PACKAGE = 'allocation-history-reduction'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_guest_panic(row, seed, wrong):
    if seed == 42:
        function = 'first'
    elif seed == 43 and not wrong or seed == 40 and wrong:
        function = 'depends_on_api'
    elif seed == 40 and not wrong:
        function = 'third'
    else:
        require(wrong and 'guest trap: core::panicking::assert_failed' in row['stderr'] and
                'in rust_interp_entry[]' in row['stderr'], 'wrong body did not reach the unchanged equality assertion')
        return
    require('guest trap: std::rt::panic_fmt' in row['stderr'] and 'in ' + function + '[]' in row['stderr'],
            'literal probe did not reach its expected panic site')


def dump_inventory(directory):
    entries, total = {}, 0
    for path in sorted(directory.iterdir()):
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and path.suffix == '.mir' and len(entries) < 2048,
                'unexpected or excessive MIR dumps')
        total += info.st_size
        require(total <= 64 * 1024 * 1024, 'MIR dumps exceed byte bound')
        entries[path.name] = dict(inode=info.st_ino, bytes=info.st_size,
            mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns, sha256=sha(path))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--dump-mir', action='store_true', help='observe MIR pass output and compare bytecode to the uninstrumented reduction')
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['', '.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_space(ROOT / '.work', 8)
        tool, key = installed_tools(TOOL)
        require_export_option(tool, key, 'allocation-trace')
        binaries = json.loads((tool / 'ready.json').read_text())
        std_key = checked_std_mir(TOOLCHAIN)[2]
        qualification = ROOT / 'results/allocation-trace-launcher-02/summary.json'
        q = json.loads(qualification.read_text())
        require(q['status'] == 'passed' and q['binaries']['traced'] == binaries and
                q['sources_sha256']['scripts/interpreter.py'] == sha(ROOT / 'scripts/interpreter.py'),
                'launcher qualification differs')
        raw, out = [ROOT / parent / args.run_id for parent in ['.work/runs', 'results']]
        require(not raw.exists() and not out.exists(), 'reduction identity already exists')
        raw.mkdir()
        fixture = raw / 'fixture'
        fixture.mkdir()
        original_path = ROOT / 'tests/allocation_history_fixture.rs'
        source = fixture / 'lib.rs'
        original = original_path.read_bytes()
        source.write_bytes(original)
        manifest = fixture / 'Cargo.toml'
        manifest.write_text('[package]\nname="' + PACKAGE + '"\nversion="0.0.0"\nedition="2024"\n'
                            '[lib]\npath="lib.rs"\n[workspace]\n')
        marker = b'// Keep all workload code and assertions below this marker unchanged across edits.'
        require(original.count(marker) == 1 and original.count(b'panic!("Expected OneOf")') == 3,
                'fixture marker or literal sites differ')
        before = b'pub fn identity(value: u64) -> u64 { value }'
        require(original.count(before) == 1, 'API edit must match exactly once')
        states = [('original', original),
            ('wrong', original.replace(before, b'pub fn identity(value: u64) -> u64 { value.wrapping_add(1) }')),
            ('api', original.replace(before, b'pub fn identity(value: impl Into<u64>) -> u64 { value.into() }')),
            ('restored', original)]
        require(all(payload.split(marker)[1] == original.split(marker)[1] for _, payload in states),
                'workload or assertions changed')
        inputs = [Path(__file__), original_path, manifest, qualification, tool / 'ready.json',
            tool / 'capabilities.json', *(ROOT / 'scripts' / p for p in
            ['interpreter.py', 'allocation_trace.py', 'std_mir.py', 'workflow_io.py', 'verify_repeated_workflow.py']),
            *(Path(__file__).with_name(p) for p in
            ['inspect_allocation_origins.py', 'check_allocation_trace.py', 'qualify_trace_launcher.py'])]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        reference = None
        dump_directories = {}
        if args.dump_mir:
            reference_path = ROOT / 'results/allocation-history-reduction-02/summary.json'
            reference = json.loads(reference_path.read_text())
            require(reference['status'] == 'completed diagnostic' and reference['binaries'] == binaries and
                    reference['sources_sha256']['tests/allocation_history_fixture.rs'] == sha(original_path),
                    'uninstrumented reference differs')
            frozen[str(reference_path.relative_to(ROOT))] = sha(reference_path)
            for incremental in ['1', '0']:
                dump_directories[incremental] = raw / ('mir-dumps-incremental-' + incremental)
                dump_directories[incremental].mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                   'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
        rows, observations = [], []

        def run(label, command, *, environment=env, expected=0):
            require_space(raw, 8)
            command = list(map(str, command))
            child, stdout, stderr = capture(command, cwd=ROOT, env=environment,
                receipt_path=raw / 'active-command.json', receipt=dict(label=label))
            row = dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                incremental=environment.get('CARGO_INCREMENTAL'), source_sha256=sha(source), stdout=stdout, stderr=stderr)
            rows.append(row)
            write_json(raw / 'records.json', rows)
            require(child.returncode == expected and 'internal compiler error' not in stderr,
                    'reduction command outcome differs: ' + label)
            return row

        run('lockfile', ['cargo', '+' + TOOLCHAIN, 'generate-lockfile', '--manifest-path', manifest, '--offline'])
        frozen[str((fixture / 'Cargo.lock').relative_to(ROOT))] = sha(fixture / 'Cargo.lock')
        write_json(raw / 'plan.json', dict(tool_key=key, binaries=binaries, std_key=std_key, seeds=SEEDS,
            dump_mir=args.dump_mir,
            predicted_allocation_counts={'1': [1, 1, 2, 2], '0': [1, 1, 1, 1]},
            states=[dict(label=label, source_sha256=hashlib.sha256(payload).hexdigest()) for label, payload in states],
            sources_sha256=frozen, note='Controlled reduction; predictions are not acceptance conditions. No performance inference.'))
        with SourceEdit(source, original) as edit:
            for state, payload in states:
                if source.read_bytes() != payload:
                    edit.replace(payload)
                require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'reduction inputs changed')
                wrong = state == 'wrong'
                native = raw / ('native-' + state)
                run(state + '/native-build', ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', native])
                native_results = {}
                for seed in SEEDS:
                    bad = wrong or seed in PANIC_SEEDS
                    row = run(state + '/native/' + str(seed), [native, seed], expected=101 if bad else 0)
                    if bad:
                        require('panicked at' in row['stderr'], 'native rejection was not a Rust panic')
                        if not wrong:
                            require('Expected OneOf' in row['stderr'], 'panic probe did not reach target literal')
                        elif seed not in PANIC_SEEDS:
                            require('assertion `left == right` failed' in row['stderr'], 'wrong body did not reach unchanged assertion')
                    native_results[seed] = row
                for incremental in ['1', '0']:
                    selected_env = dict(env, CARGO_INCREMENTAL=incremental)
                    before_dumps = None
                    if args.dump_mir:
                        selected_env['RUSTFLAGS'] = '-Zdump-mir=first&built|depends_on_api&built|third&built -Zdump-mir-dir=' + str(dump_directories[incremental])
                        require(' ' not in str(dump_directories[incremental]), 'dump path cannot be represented in RUSTFLAGS')
                        before_dumps = dump_inventory(dump_directories[incremental])
                    base = [sys.executable, ROOT / 'scripts/interpreter.py', '--manifest-path', manifest,
                        '--package', PACKAGE, '--tool-key', key, '--jobs', '2', '--engine', 'jit',
                        '--inline-leaves', '--std-mir', '--allocation-trace', '--instruction-limit', '100000000',
                        '--cache-namespace', args.run_id + ':incremental-' + incremental, '--entry', 'rust_interp_entry']
                    row = run(state + '/cargo-incremental-' + incremental, [*base, '--', 7],
                              environment=selected_env, expected=int(wrong))
                    launches, traces = lines(row['stderr'], 'rust-interp-launch: '), lines(row['stderr'], 'rust-interp-allocation-trace: ')
                    require(len(launches) == len(traces) == 1 and launches[0]['allocation_trace'] == traces[0] and
                            launches[0]['tool_key'] == key and launches[0]['engine'] == 'jit' and
                            traces[0]['exporter_sha256'] == binaries['rust-interp-mir-export'], 'selected trace identity differs')
                    if wrong:
                        check_guest_panic(row, 7, wrong)
                    else:
                        require(row['stdout'] == native_results[7]['stdout'], 'custom/native result differs')
                    artifact = Path(launches[0]['artifact_path'])
                    require(artifact.is_relative_to(ROOT / '.work/interpreter-workspaces' / key), 'unexpected selected artifact')
                    receipt = selected_trace(artifact)
                    require(all(traces[0].get(k) == v for k, v in receipt.items()), 'selected diagnostic changed')
                    saved = raw / (state + '-incremental-' + incremental + '.rbc')
                    trace = Path(str(saved) + '.allocations.jsonl')
                    saved.write_bytes(artifact.read_bytes())
                    trace.write_bytes(Path(receipt['path']).read_bytes())
                    require(sha(saved) == receipt['artifact_sha256'] and sha(trace) == receipt['sha256'], 'snapshot differs')
                    query = inspect(trace, saved, b'Expected OneOf')
                    query_path = raw / (state + '-incremental-' + incremental + '-origins.json')
                    write_json(query_path, query)
                    for engine in ['jit', 'interpreter']:
                        for seed in SEEDS:
                            bad = wrong or seed in PANIC_SEEDS
                            executed = run(state + '/' + incremental + '/' + engine + '/' + str(seed),
                                [tool / 'rust-interp-vm', '--engine', engine, '--instruction-limit', '100000000', saved, seed],
                                expected=int(bad))
                            if bad:
                                check_guest_panic(executed, seed, wrong)
                            else:
                                require(executed['stdout'] == native_results[seed]['stdout'], 'native/guest result differs')
                    observation = dict(state=state, incremental=incremental, allocations=len(query['matches']),
                        origins=sum(len(m['origins']) for m in query['matches']), artifact=str(saved.relative_to(ROOT)),
                        trace=str(trace.relative_to(ROOT)), artifact_sha256=sha(saved), trace_sha256=sha(trace),
                        query=str(query_path.relative_to(ROOT)), query_sha256=sha(query_path))
                    if args.dump_mir:
                        after_dumps = dump_inventory(dump_directories[incremental])
                        require(set(before_dumps).issubset(after_dumps), 'a MIR dump disappeared')
                        changed = [name for name, info in after_dumps.items() if before_dumps.get(name) != info]
                        dump_record = raw / (state + '-incremental-' + incremental + '-dump-changes.json')
                        write_json(dump_record, dict(directory=str(dump_directories[incremental].relative_to(ROOT)),
                            before=before_dumps, after=after_dumps, changed_files=changed, rustflags=selected_env['RUSTFLAGS']))
                        matched = [o for o in reference['observations'] if o['state'] == state and o['incremental'] == incremental]
                        require(len(matched) == 1 and sha(ROOT / matched[0]['artifact']) == matched[0]['artifact_sha256'],
                                'reference artifact differs')
                        observation.update(dump_changes=str(dump_record.relative_to(ROOT)),
                            dump_changes_sha256=sha(dump_record), dump_files_written=len(changed),
                            reference_artifact_identical=sha(saved) == matched[0]['artifact_sha256'])
                    observations.append(observation)
                    write_json(raw / 'observations.json', observations)
                print(json.dumps(dict(state=state, allocations=[o['allocations'] for o in observations[-2:]], commands=len(rows))), flush=True)
        require(source.read_bytes() == original and all(sha(ROOT / p) == d for p, d in frozen.items()),
                'restoration or frozen source differs')
        installed_tools(key)
        out.mkdir()
        counts = {inc: [o['allocations'] for o in observations if o['incremental'] == inc] for inc in ['1', '0']}
        write_json(out / 'summary.json', dict(status='completed diagnostic', tool_key=key, binaries=binaries, std_key=std_key,
            dump_mir=args.dump_mir,
            all_reference_artifacts_identical=all(o.get('reference_artifact_identical', False) for o in observations) if args.dump_mir else None,
            commands=len(rows), observations=observations, allocation_counts=counts,
            predicted_split_reproduced=counts == {'1': [1, 1, 2, 2], '0': [1, 1, 1, 1]},
            original_assertions_unchanged=True, wrong_body_assertions_verified=True, source_restored=True,
            sources_sha256=frozen, records_sha256=sha(raw / 'records.json'), raw=str(raw.relative_to(ROOT)),
            note='Reduced scalar workload, not large-project performance. Distinct equal-content allocation IDs are preserved. Incremental-on/off comparison does not itself name individual reused rustc queries.'))
        print(json.dumps(dict(status='completed diagnostic', commands=len(rows), allocation_counts=counts)))


if __name__ == '__main__':
    main()

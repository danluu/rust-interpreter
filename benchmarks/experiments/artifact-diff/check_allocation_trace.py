#!/usr/bin/env python3
"""Qualify allocation observation with unchanged constants/static/TLS/caller fixtures."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from interpreter import installed_tools, require_export_option, TOOLCHAIN
from std_mir import checked_std_mir
from verify_repeated_workflow import require
from workflow_io import require_space, write_json

BASELINE = '78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d'
STD = 'bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
FIXTURES = ['scalar_constant', 'static', 'tls', 'caller']
SEEDS = [*range(11), 2**63, 2**64 - 1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_trace(path, artifact):
    require(0 < path.stat().st_size <= 64 * 1024 * 1024, 'trace size out of bounds')
    events, functions, allocations, tls, materialization_bytes = [], {}, {}, {}, {}
    kinds, edges, edge_requests = Counter(), Counter(), Counter()
    requests, resolved = set(), set()
    known_kinds = {'allocation-trace', 'function', 'constant-origin', 'caller-location-origin',
        'vtable-origin', 'allocation-request', 'allocation-kind', 'materialization',
        'allocation-resolved', 'relocation', 'tls-request', 'tls-resolved', 'complete'}
    with path.open() as stream:
        for index, line in enumerate(stream):
            require(index < 1_000_000, 'trace event count out of bounds')
            event = json.loads(line)
            require(type(event.get('event')) is int and event['event'] == index, 'trace event IDs differ')
            parent = event.get('parent')
            require(parent is None or type(parent) is int and 0 <= parent < index, 'invalid parent edge')
            kind = event['kind']
            require(kind in known_kinds, 'unknown allocation trace event')
            kinds[kind] += 1
            if kind == 'function':
                require(event['index'] == event['function_index'] and event['instance_kind'] and
                        'generic_arguments' in event, 'incomplete compiler instance identity')
                functions[event['index']] = event
            function = event.get('function_index')
            require(function is None or function in functions, 'unknown originating function')
            if kind == 'allocation-request':
                requests.add(index)
                identity = event['allocation_id']
                require(event['cache_hit'] == (identity in allocations), 'allocation cache-hit trace differs')
                require(event['cached_pointer'] == allocations.get(identity), 'cached pointer differs')
            elif kind == 'materialization':
                raw = bytes.fromhex(event['bytes_hex'])
                materialization_bytes[index] = raw
                mask = bytes.fromhex(event['initialized_bits_hex'])
                size = event['size']
                require(len(raw) == size <= 16 * 1024 * 1024 and len(mask) == (size + 7) // 8,
                        'materialization bytes/mask size differs')
                if size % 8:
                    require(mask[-1] >> (size % 8) == 0, 'initialization mask contains excess bits')
                alignment = event['alignment']
                require(alignment > 0 and alignment & (alignment - 1) == 0 and
                        event['reserved_alignment'] == max(alignment, 16) and
                        event['pointer'] % alignment == 0, 'materialization alignment differs')
                identity = event['allocation_id']
                require((identity is None) != (event['tls_definition'] is None), 'ambiguous allocation origin')
                if identity is not None:
                    require(identity not in allocations, 'allocation materialized twice')
                    allocations[identity] = event['pointer']
                elif event['tls_definition'] is not None:
                    request = events[parent]
                    require(request['kind'] == 'tls-request', 'TLS materialization lacks request')
                    tls[request['definition_id']] = event['pointer']
            elif kind == 'allocation-resolved':
                require(parent not in resolved, 'request resolved twice')
                resolved.add(parent)
                request = events[parent]
                identity = event['allocation_id']
                require(request['kind'] == 'allocation-request' and request['allocation_id'] == identity,
                        'allocation resolution lacks matching request')
                require(identity not in allocations or allocations[identity] == event['pointer'],
                        'allocation identity changed pointer')
                allocations[identity] = event['pointer']
            elif kind == 'relocation':
                materialized = events[parent]
                require(materialized['kind'] == 'materialization', 'relocation lacks materialization')
                raw = materialization_bytes[parent]
                offset = event['byte_offset']
                require(0 <= offset <= len(raw) - 8 and int.from_bytes(raw[offset:offset + 8], 'little') ==
                        event['relative_value'], 'pre-rebase relocation bytes differ')
                edges[parent] += 1
            elif kind == 'tls-request':
                requests.add(index)
                identity = event['definition_id']
                require(event['cache_hit'] == (identity in tls) and event['cached_pointer'] == tls.get(identity),
                        'TLS cache trace differs')
            elif kind == 'tls-resolved':
                require(parent not in resolved, 'TLS request resolved twice')
                resolved.add(parent)
                request = events[parent]
                require(request['kind'] == 'tls-request' and tls[request['definition_id']] == event['pointer'],
                        'TLS resolution differs')
            if kind == 'allocation-request' and parent is not None and events[parent]['kind'] == 'relocation':
                require(events[parent]['target_allocation_id'] == event['allocation_id'], 'relocation target differs')
                edge_requests[parent] += 1
            events.append(event)
    require(events[0]['kind'] == 'allocation-trace' and events[0]['schema_version'] == 1 and
            events[0]['strict_frontend'] is True and kinds['allocation-trace'] == 1 and kinds['complete'] == 1,
            'missing or repeated trace boundary')
    require(events[-1]['kind'] == 'complete' and events[-1]['prior_events'] == len(events) - 1 and
            events[-1]['artifact_sha256'] == sha(artifact), 'trace is incomplete or belongs to another artifact')
    require(requests == resolved, 'trace contains unresolved requests')
    for event in events:
        if event['kind'] == 'materialization':
            require(edges[event['event']] == event['relocation_count'], 'relocation events missing')
        elif event['kind'] == 'relocation':
            require(edge_requests[event['event']] == 1, 'relocation lacks exactly one target request')
    return dict(events=len(events), kinds=dict(kinds), allocations=len(allocations), tls=len(tls),
        functions=len(functions), bytes=path.stat().st_size, trace_sha256=sha(path), artifact_sha256=sha(artifact),
        cache_hits=sum(e['kind'] == 'allocation-request' and e['cache_hit'] for e in events),
        partially_initialized_allocations=sum(e['kind'] == 'materialization' and
            sum(bin(byte).count('1') for byte in bytes.fromhex(e['initialized_bits_hex'])) < e['size'] for e in events))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tool-key', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require_space(ROOT / '.work', 8)
        tool, key = installed_tools(args.tool_key)
        baseline, _ = installed_tools(BASELINE)
        manifests = {label: json.loads((directory / 'ready.json').read_text())
                     for label, directory in [('baseline', baseline), ('diagnostic', tool)]}
        require_export_option(tool, key, 'allocation-trace')
        require(sha(tool / 'rust-interp-vm') == sha(baseline / 'rust-interp-vm'), 'diagnostic changed the VM')
        require((ROOT / '.work/std-mir' / STD / 'ready.json').exists(), 'pinned std-MIR is not installed')
        sysroot, _, std_key, _ = checked_std_mir(TOOLCHAIN)
        require(std_key == STD, 'std-MIR identity differs')
        raw, out = ROOT / '.work/runs' / args.run_id, ROOT / 'results' / args.run_id
        require(not raw.exists() and not out.exists(), 'qualification identity already exists')
        raw.mkdir()
        sources = [ROOT / 'tests' / (fixture + '_fixture.rs') for fixture in FIXTURES]
        helpers = ['interpreter.py', 'std_mir.py', 'verify_repeated_workflow.py', 'workflow_io.py',
                   'workflow_jobs.py', 'workflow_measurements.py', 'workflow_case_file.py']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in
                  [Path(__file__), *sources, *(ROOT / 'scripts' / name for name in helpers)]}
        rows, observations = [], []

        def run(label, command, env=None, expected=0):
            command = list(map(str, command))
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            record = dict(label=label, command=command, pid=child.pid, parent_pid=os.getpid(),
                          cwd=str(ROOT), started_at=time.time(), status='running',
                          export_environment={k: v for k, v in (env or {}).items() if k.startswith('RUST_INTERP_')})
            try:
                write_json(raw / 'active-command.json', record)
            finally:
                stdout, stderr = child.communicate()
            record.update(status='finished', returncode=child.returncode, stdout=stdout,
                          stderr=stderr, finished_at=time.time())
            rows.append(record)
            write_json(raw / 'active-command.json', record)
            write_json(raw / 'records.json', rows)
            require(child.returncode == expected and 'internal compiler error' not in stderr,
                    'qualification command failed: ' + label)
            return stdout.strip()

        environment = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'CARGO_PROFILE_'))
                       and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER',
                                     'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL']}
        for fixture, source in zip(FIXTURES, sources):
            work = raw / fixture
            work.mkdir()
            native = work / 'native'
            run(fixture + ':native-build', ['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', native], environment)
            # Fresh processes preserve the TLS fixture's original contract.
            expected = {seed: run(f'{fixture}:native:{seed}', [native, seed], environment) for seed in SEEDS}
            artifacts = []
            for label, compiler, traced in [('baseline', baseline, False), ('disabled', tool, False), ('enabled', tool, True)]:
                stage = work / label
                stage.mkdir()
                artifact = stage / 'program.rbc'
                env = dict(environment, RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='rust_interp_entry')
                if traced:
                    env['RUST_INTERP_ALLOCATION_TRACE'] = '1'
                run(f'{fixture}:export:{label}', [compiler / 'rust-interp-mir-export', source,
                    '--crate-name', 'allocation_trace_case', '--edition=2024', '--emit=metadata',
                    '--sysroot', sysroot, '-o', stage / 'program.rmeta'], env)
                artifacts.append(artifact)
                if traced:
                    observations.append(dict(fixture=fixture, **verify_trace(
                        artifact.with_name(artifact.name + '.allocations.jsonl'), artifact)))
                for engine in ['interpreter', 'jit']:
                    for seed in SEEDS:
                        actual = run(f'{fixture}:{label}:{engine}:{seed}',
                                     [tool / 'rust-interp-vm', '--engine', engine, artifact, seed], environment)
                        require(actual == expected[seed], 'native/guest result differs')
            require(len({sha(p) for p in artifacts}) == 1, 'diagnostic changes exported artifact')
        rejected = []
        for label, settings, diagnostic in [
            ('invalid-value', {'RUST_INTERP_ALLOCATION_TRACE': '0'}, 'must be 1 when set'),
            ('partial-checking', {'RUST_INTERP_DEMAND_BODIES': '1'}, 'requires strict checking'),
            ('audit-selection', {'audit': True}, 'requires strict checking'),
        ]:
            stage = raw / ('rejected-' + label)
            stage.mkdir()
            artifact = stage / 'program.rbc'
            trace = stage / 'program.rbc.allocations.jsonl'
            artifact.write_bytes(b'old artifact')
            trace.write_bytes(b'old trace')
            env = dict(environment, RUST_INTERP_OUTPUT=str(artifact), RUST_INTERP_ENTRY='rust_interp_entry',
                       RUST_INTERP_ALLOCATION_TRACE='1')
            if settings.get('audit'):
                selection = stage / 'selection.json'
                write_json(selection, ['rust_interp_entry'])
                env.pop('RUST_INTERP_ENTRY')
                env['RUST_INTERP_AUDIT_SELECTION'] = str(selection)
            else:
                env.update(settings)
            run('reject:' + label, [tool / 'rust-interp-mir-export', sources[0],
                '--crate-name', 'allocation_trace_case', '--edition=2024', '--emit=metadata',
                '-o', stage / 'program.rmeta'], env, expected=2)
            require(diagnostic in rows[-1]['stderr'] and not artifact.exists() and not trace.exists(),
                    'invalid trace mode was not rejected or retained stale standalone output')
            rejected.append(label)
        require(all(sha(ROOT / p) == digest for p, digest in frozen.items()), 'qualification sources changed')
        for label, directory in [('baseline', baseline), ('diagnostic', tool)]:
            require(json.loads((directory / 'ready.json').read_text()) == manifests[label] and
                    all(sha(directory / name) == digest for name, digest in manifests[label].items()),
                    'immutable tool changed during qualification')
        require(sum(o['kinds'].get('relocation', 0) for o in observations) > 0 and
                sum(o['cache_hits'] for o in observations) > 0 and
                sum(o['tls'] for o in observations) > 0 and
                sum(o['partially_initialized_allocations'] for o in observations) > 0,
                'fixtures did not cover relocation, caching, TLS and initialization masks')
        out.mkdir()
        write_json(out / 'summary.json', dict(status='passed', tool_key=key, baseline_tool_key=BASELINE,
            std_mir_key=STD, commands=len(rows), fixtures=observations, rejected_modes=rejected,
            binaries=manifests, sources_sha256=frozen,
            records_sha256=sha(raw / 'records.json'), raw=str(raw.relative_to(ROOT)),
            note='Existing fixture assertions are unchanged. Each seed executes in a fresh native process and both custom engines. All baseline/disabled/enabled bytecode must match. These are diagnostic qualifications, not performance samples.'))
        print(json.dumps(dict(status='passed', commands=len(rows), fixtures=len(observations))))


if __name__ == '__main__':
    main()

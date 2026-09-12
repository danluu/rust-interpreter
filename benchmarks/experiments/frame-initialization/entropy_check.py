#!/usr/bin/env python3
"""Qualify exact entropy replay before using it with unchanged owned VMs."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/tuned-native'))
from compare_saved_runtime import acquire_lock
from timing import environment, invoke, sha, require
from workflow_io import write_json as write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(Path(run).name == run and run.startswith('fixed-frame-clear-entropy-check-'), 'invalid run ID')
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        paths = [Path(__file__), HERE / 'entropy_replay.c', HERE / 'entropy_fixture.c', HERE / 'ENTROPY.md']
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        env = environment('repository')
        require(not any(k.startswith('DYLD_') for k in env), 'existing dynamic-loader instrumentation is out of scope')
        write(work / 'plan.json', dict(owner=str(ROOT), pid=os.getpid(), frozen=frozen,
            performance_measurement=False, scope='Owned entropy fixture only; no VM benchmark yet.'))
        records = []

        def call(label, command, selected=env, expected=0, message=None):
            row, stdout, stderr = invoke(work, label, command, ROOT, selected)
            records.append(row)
            write(work / 'records.json', records)
            require(row['returncode'] == expected, 'unexpected result: ' + label)
            require(message is None or message in stderr, 'wrong rejection: ' + label)
            return stdout, stderr

        library, fixture = work / 'entropy.dylib', work / 'fixture'
        common = ['xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror']
        call('build-library', [*common, '-dynamiclib', str(HERE / 'entropy_replay.c'), '-o', str(library)])
        call('build-fixture', [*common, str(HERE / 'entropy_fixture.c'), '-o', str(fixture)])
        frozen.update({str(p.relative_to(ROOT)): sha(p) for p in [library, fixture]})
        tape = work / 'original.tape'

        def fixture_call(label, mode, path=tape, argument='normal', expected=0, message=None):
            selected = dict(env, DYLD_INSERT_LIBRARIES=str(library), RUST_INTERP_ENTROPY_MODE=mode,
                RUST_INTERP_ENTROPY_TAPE=str(path))
            return call(label, [str(fixture), argument], selected, expected, message)

        original, stderr = fixture_call('record', 'record')
        require('entropy_calls=3 entropy_bytes=50' in stderr, 'recorded wrong request count')
        payload = tape.read_bytes()
        require(payload[:8] == b'RIRNG001' and stat.S_IMODE(tape.stat().st_mode) == 0o600, 'invalid tape header/mode')
        at, checksum = 8, 14695981039346656037
        for size in [1, 16, 33]:
            require(int.from_bytes(payload[at:at + 8], 'little') == size, 'tape request size differs')
            at += 8
            for byte in payload[at:at + size]:
                checksum = ((checksum ^ byte) * 1099511628211) % 2**64
            at += size
        require(at == len(payload) and original == str(checksum) + '\n', 'recorded bytes do not reproduce fixture output')
        tape_hash = sha(tape)
        for index in range(2):
            output, errors = fixture_call('replay-' + str(index), 'replay')
            require(output == original and 'entropy_calls=3 entropy_bytes=50' in errors, 'replay bytes/counts differ')
        for name, message in [('different', 'request length differs'), ('short', 'unconsumed entropy'),
                              ('extra', 'incomplete entropy'), ('thread', 'requires the main thread')]:
            fixture_call(name, 'replay', argument=name, expected=86, message=message)
        fixture_call('overwrite', 'record', expected=86, message='cannot open exclusive')
        for name, data, message in [('header', b'INVALID!' + payload[8:], 'invalid entropy tape header'),
                                   ('truncated', payload[:-1], 'incomplete entropy'),
                                   ('trailing', payload + b'x', 'unconsumed entropy')]:
            path = work / (name + '.tape')
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
            fixture_call(name, 'replay', path=path, expected=86, message=message)
        link = work / 'symlink.tape'
        link.symlink_to(tape.name)
        fixture_call('symlink', 'replay', path=link, expected=86, message='cannot open exclusive')
        fixture_call('bad-mode', 'unknown', expected=86, message='unknown entropy mode')
        empty = work / 'empty.tape'
        for mode in ['record', 'replay']:
            output, errors = fixture_call('empty-' + mode, mode, path=empty, argument='none')
            require(output == '' and 'entropy_calls=0 entropy_bytes=0' in errors, 'empty stream differs')
        require(empty.read_bytes() == b'RIRNG001', 'empty tape differs')
        require(sha(tape) == tape_hash and all(sha(ROOT / p) == h for p, h in frozen.items()), 'qualified input changed')
        result = dict(status='passed', commands=len(records), fixture_commands=len(records) - 2,
            expected_rejections=sum(r['returncode'] == 86 for r in records), performance_measurement=False,
            library=str(library.relative_to(ROOT)), library_sha256=sha(library), fixture_sha256=sha(fixture),
            tape_sha256=tape_hash, raw=str(work.relative_to(ROOT)), frozen=frozen,
            evidence={str(p.relative_to(ROOT)): sha(p) for p in [work / 'plan.json', work / 'records.json']})
        write(work / 'summary.json', result)
        out = ROOT / 'results' / run
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()

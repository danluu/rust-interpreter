#!/usr/bin/env python3
"""Validate normal Darwin stripping and loading of stripped proc macros."""
import argparse
import atexit
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import struct

from owned_stage import CANONICAL_LOCK, workload_lock

parser = argparse.ArgumentParser()
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--package-provenance', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--lock-wait-seconds', type=int, default=45)
parser.add_argument('--lock-fd', type=int)
parser.add_argument('--partitioning-policy', choices=['stable-cgu', 'stable-mono-cgu'], default='stable-cgu')
args = parser.parse_args()
if not __debug__:
    raise RuntimeError('strip controls require Python assertion checking')
assert 0 < args.lock_wait_seconds <= 1800
args.compiler = args.compiler.resolve(strict=True)
args.package_provenance = args.package_provenance.resolve(strict=True)
args.receipt = args.receipt.resolve()
args.receipt.mkdir(parents=True, exist_ok=False)
provenance = json.loads(args.package_provenance.read_text())
package_receipt = args.package_provenance.parent / 'receipt.json'
assert hashlib.sha256(package_receipt.read_bytes()).hexdigest() == provenance['package_receipt_sha256']
package = json.loads(package_receipt.read_text())
prefix = args.compiler.parent.parent
assert Path(package['prefix']) == prefix
assert package['files']['bin/rustc'] == hashlib.sha256(args.compiler.read_bytes()).hexdigest()
record = {'schema_version': 1, 'supervisor_pid': os.getpid(), 'started_at': time.time(),
          'compiler': str(args.compiler),
          'compiler_sha256': hashlib.sha256(args.compiler.read_bytes()).hexdigest(),
          'package_provenance_sha256': hashlib.sha256(args.package_provenance.read_bytes()).hexdigest(),
          'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'partitioning_policy': args.partitioning_policy, 'inherited_lock_fd': args.lock_fd,
          'lock_wait_limit_seconds': args.lock_wait_seconds,
          'status': 'waiting for shared lock', 'commands': [], 'histories': []}


def save():
    (args.receipt / 'result.json').write_text(json.dumps(record, indent=2) + '\n')


save()
lock_scope = ExitStack()
atexit.register(lock_scope.close)
print('Owned native-control supervisor', os.getpid(), 'waiting for shared slot', flush=True)
try:
    lock_scope.enter_context(workload_lock(CANONICAL_LOCK, args.lock_wait_seconds, args.lock_fd))
except TimeoutError:
    record.update(status='lock admission timed out; no compiler started', finished_at=time.time())
    save()
    raise SystemExit(1)
assert shutil.disk_usage(args.receipt).free >= 9 * 2**30
for name, expected in package['files'].items():
    assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == expected, name
record.update(status='running', lock_acquired_at=time.time())
save()
environment = os.environ.copy()
assert not any(name.startswith(('LD_', 'DYLD_')) for name in environment)
for name in ['RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS',
             'CARGO_ENCODED_RUSTFLAGS', 'RUST_SYSROOT']:
    environment.pop(name, None)


def command(argv):
    index = len(record['commands'])
    stdout_path = args.receipt / f'{index:02d}.stdout'
    stderr_path = args.receipt / f'{index:02d}.stderr'
    with stdout_path.open('w') as stdout, stderr_path.open('w') as stderr:
        child = subprocess.Popen(argv, cwd=args.receipt, env=environment, stdout=stdout, stderr=stderr)
        try:
            identity = subprocess.run(['ps', '-p', str(child.pid), '-o', 'pid,ppid,lstart,command'],
                                      text=True, capture_output=True)
            item = {'argv': argv, 'pid': child.pid, 'started_at': time.time(),
                    'identity': identity.stdout.strip(), 'identity_status': identity.returncode}
            record['commands'].append(item)
            save()
        finally:
            returncode = child.wait()
    item.update(returncode=returncode, finished_at=time.time(),
                stdout_sha256=hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
                stderr_sha256=hashlib.sha256(stderr_path.read_bytes()).hexdigest())
    save()
    assert returncode == 0, (argv, stderr_path.read_text())
    assert 'stripping' not in stderr_path.read_text().lower(), stderr_path.read_text()
    return stdout_path.read_text()


def symbol_stats(path):
    data = path.read_bytes()
    assert struct.unpack_from('<I', data)[0] == 0xfeedfacf
    count = struct.unpack_from('<I', data, 16)[0]
    offset = 32
    found = None
    for _ in range(count):
        command_kind, size = struct.unpack_from('<II', data, offset)
        assert size >= 8 and offset + size <= len(data)
        if command_kind == 2:  # LC_SYMTAB, with 64-bit nlist records.
            symbol_offset, symbol_count, string_offset, string_size = struct.unpack_from('<4I', data, offset + 8)
            assert symbol_offset + symbol_count * 16 <= len(data)
            assert string_offset + string_size <= len(data)
            types = [data[symbol_offset + index * 16 + 4] for index in range(symbol_count)]
            found = {'symbols': symbol_count, 'debug_symbols': sum(bool(kind & 0xe0) for kind in types)}
        offset += size
    assert found is not None
    return found


(args.receipt / 'binary.rs').write_text('fn main() { println!("{}", std::hint::black_box(17u64)); }\n')
(args.receipt / 'macro.rs').write_text('extern crate proc_macro; #[proc_macro] pub fn answer(_: proc_macro::TokenStream) -> proc_macro::TokenStream { "17u64".parse().unwrap() }\n')
(args.receipt / 'consumer.rs').write_text('fn main() { println!("{}", strip_macro::answer!()); }\n')
stats = {}
policy_flags = (['-Zstable-cgu-partitioning=no', '-Zstable-mono-cgu-partitioning=yes']
                if args.partitioning_policy == 'stable-mono-cgu'
                else ['-Zstable-cgu-partitioning=true'])
for kind in ['binary', 'proc-macro']:
    stats[kind] = {}
    for mode in ['none', 'debuginfo', 'symbols']:
        target = args.receipt / (f'binary-{mode}' if kind == 'binary' else f'libstrip_macro-{mode}.dylib')
        argv = [str(args.compiler), 'binary.rs' if kind == 'binary' else 'macro.rs',
                '--edition=2021', '--crate-name=' + ('strip_binary' if kind == 'binary' else 'strip_macro'),
                '--crate-type=' + ('bin' if kind == 'binary' else 'proc-macro'),
                '-Zunstable-options', '--jobs-backend=2', '-Ccodegen-units=2',
                '-Cdebuginfo=2', '-Cstrip=' + mode, '-Cincremental=cache-' + kind,
                *policy_flags, '-o', str(target)]
        command(argv)
        stats[kind][mode] = symbol_stats(target)
        if kind == 'binary':
            assert command([str(target)]).strip() == '17'
        else:
            consumer = args.receipt / ('consumer-' + mode)
            command([str(args.compiler), 'consumer.rs', '--edition=2021',
                     '-Zunstable-options', '--jobs-backend=2',
                     *(policy_flags if args.partitioning_policy == 'stable-mono-cgu' else []),
                     '--extern', 'strip_macro=' + str(target), '-o', str(consumer)])
            assert command([str(consumer)]).strip() == '17'
        record['histories'].append({'kind': kind, 'strip': mode, 'artifact': str(target),
                                    'partitioning_policy': args.partitioning_policy,
                                    'artifact_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                                    'symbol_stats': stats[kind][mode], 'expected_output': '17'})
        save()
    assert stats[kind]['none']['debug_symbols'] > 0, stats[kind]
    assert stats[kind]['debuginfo']['debug_symbols'] == 0, stats[kind]
    assert stats[kind]['symbols']['debug_symbols'] == 0, stats[kind]
    assert stats[kind]['symbols']['symbols'] <= stats[kind]['debuginfo']['symbols'], stats[kind]

for name, expected in package['files'].items():
    assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == expected, name
record.update(status='passed', finished_at=time.time(), package_files_unchanged=len(package['files']),
              compiler_unchanged=True, symbol_stats=stats,
              source_files={path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in args.receipt.glob('*.rs')})
save()
print('6 native strip-mode states passed, including3 stripped-proc-macro compile/load/execute controls')

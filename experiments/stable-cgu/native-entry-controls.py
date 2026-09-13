#!/usr/bin/env python3
"""Validate actual native entrypoints while stable CGU merging is active."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--package-provenance', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--lock-wait-seconds', type=int, default=45)
args = parser.parse_args()
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
          'lock_wait_limit_seconds': args.lock_wait_seconds,
          'status': 'waiting for shared lock', 'commands': [], 'histories': []}


def save():
    (args.receipt / 'result.json').write_text(json.dumps(record, indent=2) + '\n')


save()
lock = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock').open('a+')
def admission_timeout(signum, frame):
    raise TimeoutError('shared resource admission deadline')
previous_alarm = signal.signal(signal.SIGALRM, admission_timeout)
signal.alarm(args.lock_wait_seconds)
print('Owned native-control supervisor', os.getpid(), 'waiting for shared slot', flush=True)
try:
    fcntl.flock(lock, fcntl.LOCK_EX)
except TimeoutError:
    record.update(status='lock admission timed out; no compiler started', finished_at=time.time())
    save()
    raise SystemExit(1)
finally:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous_alarm)
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
    return stdout_path.read_text()


def source(edited):
    text = ('static VALUE: u64 = 9; static REFERENCE: &u64 = &VALUE;\n'
            'std::thread_local! { static LOCAL: std::cell::Cell<u64> = const { std::cell::Cell::new(7) }; }\n'
            '#[inline(always)] fn twice<T: Into<u64>>(x: T) -> u64 { x.into() * 2 }\n')
    for index in range(65):
        value = 100 if index == 0 and edited else index
        text += f'mod m{index} {{ #[inline(never)] pub fn value(x: u64) -> u64 {{ super::twice(x) + {value} }} }}\n'
    text += ('fn main() { assert_eq!(*REFERENCE, 9); '
             'LOCAL.with(|v| { assert_eq!(v.replace(8), 7); v.set(7); }); '
             'let x = std::hint::black_box(10u64); let result = 0')
    text += ''.join(f' + m{index}::value(x)' for index in range(65))
    return text + '; println!("{}", result); }\n'


for label, edited in [('original', False), ('edited', True)]:
    (args.receipt / f'{label}.rs').write_text(source(edited))

for count in [1, 4, 64]:
    for state, edited, enabled in [('cold', False, True), ('edited', True, True),
                                   ('restored', False, True), ('off', False, False),
                                   ('on', False, True)]:
        (args.receipt / 'main.rs').write_text(source(edited))
        argv = [str(args.compiler), 'main.rs', '--edition=2021', '--crate-name=native_entry',
                '-Zunstable-options', '--jobs-backend=2',
                '-o', 'native-entry', f'-Ccodegen-units={count}', '-Cdebuginfo=2',
                f'-Cincremental=cache-{count}', '-Zhuman-readable-cgu-names',
                '-Zprint-mono-items=yes', '-Zquery-dep-graph',
                f'-Zstable-cgu-partitioning={str(enabled).lower()}']
        output = command(argv)
        reuse = {}; occupied = set()
        for line in output.splitlines():
            if line.startswith('CGU_REUSE '):
                name, kind = line.removeprefix('CGU_REUSE ').split(' ', 1)
                reuse[name] = kind
            elif line.startswith('MONO_ITEM '):
                units = line.split(' @@ ', 1)[1]
                occupied.update(unit.split('[', 1)[0] for unit in units.split())
        assert len(reuse) == count, reuse
        assert any('stable-cgu-v1' in name for name in reuse) == enabled
        if enabled and count == 64:
            assert len(occupied) < count, 'empty CGU coverage was not exercised'
        expected = 65 * 20 + 65 * 64 // 2 + (100 if edited else 0)
        assert command([str(args.receipt / 'native-entry')]).strip() == str(expected)
        record['histories'].append({'count': count, 'state': state, 'enabled': enabled,
                                    'source_sha256': hashlib.sha256((args.receipt / 'main.rs').read_bytes()).hexdigest(),
                                    'binary_sha256': hashlib.sha256((args.receipt / 'native-entry').read_bytes()).hexdigest(),
                                    'reuse': reuse, 'occupied_cgus': len(occupied),
                                    'expected_output': expected})
        save()

for name, expected in package['files'].items():
    assert hashlib.sha256((prefix / name).read_bytes()).hexdigest() == expected, name
record.update(status='passed', finished_at=time.time(), package_files_unchanged=len(package['files']),
              compiler_unchanged=True)
save()
print('15 native binary compile/execute states passed across CGU counts1/4/64')

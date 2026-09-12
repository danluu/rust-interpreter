"""Validate selected test reports without accepting compiler/resource errors as assertions."""
import hashlib
import json

from native_suite import test_status


def guest_test_failure(stderr):
    prefix = 'rust-interp-vm: guest trap: '
    for line in stderr.splitlines():
        if line.startswith('rust-interp-vm: guest assertion: ') and line.removeprefix('rust-interp-vm: guest assertion: '):
            return True
        if not line.startswith(prefix):
            continue
        message = line.removeprefix(prefix)
        if 'assertion' in message or 'panicking::' in message:
            return True
        for crate in ['core', 'std']:
            for helper in ['option::unwrap_failed', 'option::expect_failed', 'result::unwrap_failed']:
                if message.startswith(crate+'::'+helper+' '):
                    return True
    return False


def read_report(path, expected_hash=None):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 16*1024*1024:
        raise RuntimeError('missing or oversized test suite report')
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if expected_hash is not None and digest != expected_hash:
        raise RuntimeError('test suite report hash differs')
    return json.loads(payload), digest


def validate_runtime_limits(report, instruction_limit=None, allocation_limit=None, *, required=False):
    """Compare VM-effective limits with independently supplied command expectations."""
    if 'runtime_limits' not in report:
        if required: raise RuntimeError('suite lacks effective runtime limits')
        return  # Older immutable VMs remain usable; they provide no effective-limit receipt.
    expected = dict(instructions=100_000_000 if instruction_limit is None else instruction_limit,
                    allocations=100_000 if allocation_limit is None else allocation_limit,
                    memory_bytes=64*1024*1024, frames=4096)
    actual = report['runtime_limits']
    if (not isinstance(actual, dict) or actual != expected or
            any(type(value) is not int for value in actual.values()) or
            type(report.get('jit_code_limit_bytes')) is not int or report['jit_code_limit_bytes'] != 16*1024*1024):
        raise RuntimeError('suite effective runtime limits differ from the expected command')


def validate_report(report, names, mode, success):
    def require(condition, message):
        if not condition:
            raise RuntimeError(message)
    require(report['schema_version'] == 1 and report['mode'] == mode, 'suite mode/schema differs')
    rows = report['tests']
    require([row['name'] for row in rows] == names and len(set(names)) == len(names), 'test names/order differ')
    require(all(row['status'] in ['passed', 'failed'] for row in rows), 'unsupported test outcome')
    failed = sum(row['status'] == 'failed' for row in rows)
    require(report['passed'] == len(names)-failed and report['failed'] == failed, 'test counts differ')
    require(report['status'] == ('passed' if success else 'failed') and (failed == 0) == success,
            'wrong-edit or passing-suite control failed')
    for row in rows:
        if mode == 'native':
            require(row['status'] == test_status(row['name'], row['returncode'], row['stdout']), 'native test status differs')
        elif row['status'] == 'failed':
            require(guest_test_failure('rust-interp-vm: '+row['error']), 'failure was not a guest assertion')
    return [(row['name'], row['status']) for row in rows]

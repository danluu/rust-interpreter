"""Validate the unchanged options-hash driver's stdout, without running it."""
import hashlib
import json


LABELS = (
    'base-first', 'base-repeat', 'tracked-change', 'base-after-tracked',
    'non-crate-tracked-change', 'base-after-lint', 'untracked-change', 'base-final',
)
MAX_BYTES = 64 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('nonfinite JSON value: ' + value)


def parse(raw, *, mode):
    """Require nine complete records and independently check all relationships.

    This checks one process only. Its stdout cannot establish compiler identity,
    loader provenance, source integrity, actual worker execution or exit status;
    the eventual caller must independently bind those to the recorded child.
    """
    require(mode in ('serial', 'parallel'), 'unknown driver mode')
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'stdout byte bound')
    # println! emits a final LF. Do not silently discard blank or trailing data.
    require(raw.endswith(b'\n'), 'unterminated stdout record')
    lines = raw[:-1].split(b'\n')
    require(len(lines) == 9 and all(lines), 'exactly nine stdout records required')
    rows = [json.loads(line.decode('utf-8', errors='strict'),
                       object_pairs_hook=unique_object, parse_constant=reject_constant)
            for line in lines]
    workers = 2 if mode == 'parallel' else 1
    for label, row in zip(LABELS, rows[:8], strict=True):
        require(type(row) is dict and set(row) == {
            'label', 'incremental_hash', 'crate_hash', 'workers', 'status',
        }, 'observation schema differs')
        require(row['label'] == label and row['status'] == 'passed',
                'observation label, order or status differs')
        require(type(row['workers']) is int and row['workers'] == workers,
                'worker count differs from process mode')
        for key in ('incremental_hash', 'crate_hash'):
            require(type(row[key]) is int and 0 <= row[key] < 2**64,
                    'hash must be an unsigned 64-bit integer')
    terminal = rows[-1]
    require(type(terminal) is dict and set(terminal) == {'status', 'contexts', 'parallel'},
            'terminal schema differs')
    require(terminal['status'] == 'passed' and type(terminal['contexts']) is int
            and terminal['contexts'] == 8 and type(terminal['parallel']) is bool
            and terminal['parallel'] == (mode == 'parallel'), 'terminal fields differ')
    base = rows[0]
    for index in (1, 3, 5, 6, 7):
        require(all(rows[index][key] == base[key]
                    for key in ('incremental_hash', 'crate_hash')),
                'repeated or restored hash differs: ' + LABELS[index])
    require(all(rows[2][key] != base[key]
                for key in ('incremental_hash', 'crate_hash')),
            'tracked option did not change both hashes')
    require(rows[4]['incremental_hash'] != base['incremental_hash']
            and rows[4]['crate_hash'] == base['crate_hash'],
            'lint option did not preserve the crate-hash distinction')
    return dict(status='validated-observations-only', mode=mode, contexts=8,
                stdout_sha256=hashlib.sha256(raw).hexdigest(), observations=rows[:8],
                terminal=terminal)

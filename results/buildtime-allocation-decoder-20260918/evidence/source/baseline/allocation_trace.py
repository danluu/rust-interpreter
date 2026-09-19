"""Bind an opt-in allocation diagnostic to Cargo's selected bytecode sidecar.

This checks transport/schema boundaries, event order and the artifact binding.
The offline origin inspector separately checks allocation/relocation semantics.
Neither check establishes equivalent allocation identities across compilations.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_BYTES = 64 * 1024 * 1024
MAX_EVENTS = 1_000_000
KINDS = frozenset([
    'allocation-trace', 'function', 'constant-origin', 'caller-location-origin',
    'vtable-origin', 'allocation-request', 'allocation-kind', 'materialization',
    'allocation-resolved', 'relocation', 'tls-request', 'tls-resolved', 'complete',
])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _read_regular(path, limit):
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'noncanonical allocation diagnostic path')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit,
            'allocation diagnostic file size or type differs')
    # Nonblocking also prevents a regular-to-FIFO replacement from hanging here.
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        require(_identity(os.fstat(stream.fileno())) == _identity(before),
                'allocation diagnostic identity changed while opening')
        data = stream.read(limit + 1)
        require(len(data) == before.st_size and
                _identity(os.fstat(stream.fileno())) == _identity(before) and
                _identity(path.lstat()) == _identity(before),
                'allocation diagnostic file changed while reading')
    return data


def _object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate allocation trace field')
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError('nonfinite allocation trace value: ' + value)


def validate_trace(data, artifact_sha256, *, max_bytes=MAX_BYTES, max_events=MAX_EVENTS):
    """Validate serialized v1 boundaries without retaining all decoded events."""
    require(isinstance(data, bytes) and 0 < len(data) <= max_bytes,
            'allocation trace exceeds byte bound or is empty')
    require(data.endswith(b'\n'), 'allocation trace lacks final newline')
    require(isinstance(artifact_sha256, str) and len(artifact_sha256) == 64 and
            all(c in '0123456789abcdef' for c in artifact_sha256),
            'invalid selected artifact digest')
    count, offset, complete = 0, 0, False
    while offset < len(data):
        require(count < max_events and not complete,
                'allocation trace exceeds event bound or continues after completion')
        end = data.index(b'\n', offset)
        event = json.loads(data[offset:end].decode('utf-8'),
                           object_pairs_hook=_object, parse_constant=_nonfinite)
        require(isinstance(event, dict) and type(event.get('event')) is int and
                event['event'] == count and event.get('kind') in KINDS,
                'allocation trace event identity differs')
        parent = event.get('parent')
        require(parent is None or type(parent) is int and 0 <= parent < count,
                'allocation trace parent is not an earlier event')
        if count == 0:
            require(event['kind'] == 'allocation-trace' and
                    type(event.get('schema_version')) is int and event['schema_version'] == 1 and
                    event.get('strict_frontend') is True,
                    'incompatible allocation trace header')
        else:
            require(event['kind'] != 'allocation-trace', 'repeated allocation trace header')
        if event['kind'] == 'complete':
            require(count > 0 and type(event.get('prior_events')) is int and
                    event['prior_events'] == count and event.get('artifact_sha256') == artifact_sha256,
                    'allocation trace completion does not match selected artifact')
            complete = True
        count += 1
        offset = end + 1
    require(complete, 'allocation trace is incomplete')
    return count


def selected_trace(artifact):
    """Read only the sidecar adjacent to this exact Cargo-selected artifact."""
    artifact = Path(artifact)
    trace = Path(str(artifact) + '.allocations.jsonl')
    try:
        program = _read_regular(artifact, MAX_BYTES)
        digest = hashlib.sha256(program).hexdigest()
        data = _read_regular(trace, MAX_BYTES)
        events = validate_trace(data, digest)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise RuntimeError('Cargo selected an invalid allocation trace; no program was run: ' + str(error)) from error
    return dict(kind='allocation-trace', schema_version=1, strict_frontend=True,
                path=str(trace), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                events=events, artifact_path=str(artifact), artifact_bytes=len(program),
                artifact_sha256=digest)

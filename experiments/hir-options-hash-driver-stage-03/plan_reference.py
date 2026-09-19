"""Lossless one-member JSON references; pure authenticated-read callbacks only.

The referenced document is already a separately frozen logical input. Nothing
is omitted from the reconstructed plan or from its full typed integrity hash.
No recursive references, imports, provider calls, or filesystem writes occur.
The caller authenticates ordinary file routes and stable identities when reading.
"""
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

POLICY = 'external-json-member-v1'
MAX_BYTES = 64 * 2**20
MAX_NODES = 4_000_000
MAX_DEPTH = 64


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for name, value in pairs:
        require(name not in result, 'duplicate JSON member')
        result[name] = value
    return result


def encoded(value):
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, 'bounded JSON structure')
        kind = type(item)
        if kind is dict:
            require(all(type(key) is str for key in item), 'string JSON keys')
            pending.extend((child, depth + 1) for child in item.values())
        elif kind is list:
            pending.extend((child, depth + 1) for child in item)
        elif kind is float:
            require(math.isfinite(item), 'finite JSON number')
        else:
            require(kind in (str, int, bool, type(None)), 'ordinary JSON value')
    result = bytearray()
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False)
    for piece in encoder.iterencode(value):
        data = piece.encode('utf-8')
        require(len(result) + len(data) + 1 <= MAX_BYTES, 'bounded encoded JSON')
        result.extend(data)
    result.extend(b'\n')
    return bytes(result)


def parsed(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'bounded exact JSON bytes')
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda value: require(False, 'nonfinite JSON token'))
    encoded(value)
    return value


def reference_value(reference, read_bytes):
    require(type(reference) is dict and set(reference) == {'path', 'sha256'}, 'exact reference')
    name, digest = reference['path'], reference['sha256']
    require(type(name) is str and name.startswith('/') and not name.startswith('//')
            and name != '/' and str(PurePosixPath(name)) == name
            and '..' not in PurePosixPath(name).parts
            and len(name.encode('utf-8')) <= 4096
            and all(ord(c) >= 32 and ord(c) != 127 for c in name), 'canonical reference path')
    require(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'exact reference digest')
    raw = read_bytes(name)
    require(type(raw) is bytes and len(raw) <= MAX_BYTES
            and hashlib.sha256(raw).hexdigest() == digest, 'authenticated referenced bytes')
    return parsed(raw)


def split(document, *, member, reference, read_bytes):
    full_bytes = encoded(document)
    full = parsed(full_bytes)
    ref = parsed(encoded(reference))
    require(type(full) is dict and type(member) is str and 0 < len(member) <= 256
            and member in full, 'explicit existing object member')
    value = reference_value(ref, read_bytes)
    require(encoded(value) == encoded(full[member]), 'referenced member differs in value or type')
    del full[member]
    wire = dict(policy=POLICY, member=member, reference=ref, remainder=full,
                integrity=dict(sha256=hashlib.sha256(full_bytes).hexdigest(), bytes=len(full_bytes)))
    encoded(wire)
    return wire


def expand(document, *, expected_reference, read_bytes):
    wire = parsed(encoded(document))
    expected = parsed(encoded(expected_reference))
    require(type(wire) is dict and set(wire) == {'policy', 'member', 'reference', 'remainder', 'integrity'}
            and wire['policy'] == POLICY, 'exact external-member envelope')
    member = wire['member']
    require(type(member) is str and 0 < len(member) <= 256 and type(wire['remainder']) is dict
            and member not in wire['remainder'], 'disjoint explicit member and remainder')
    require(encoded(wire['reference']) == encoded(expected), 'reviewed reference required')
    integrity = wire['integrity']
    require(type(integrity) is dict and set(integrity) == {'sha256', 'bytes'}
            and type(integrity['sha256']) is str and re.fullmatch('[0-9a-f]{64}', integrity['sha256'])
            and type(integrity['bytes']) is int and 0 < integrity['bytes'] <= MAX_BYTES,
            'typed complete reconstruction integrity')
    full = wire['remainder']
    full[member] = reference_value(wire['reference'], read_bytes)
    raw = encoded(full)
    require(len(raw) == integrity['bytes'] and hashlib.sha256(raw).hexdigest() == integrity['sha256'],
            'complete typed reconstruction differs')
    return full

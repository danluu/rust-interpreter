"""Lossless separation of source-bound exporter telemetry and compiler JSON."""
import hashlib
import json
import math
import re


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def parse_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON ' + value)))
    except (ValueError, UnicodeError) as error:
        raise RuntimeError('invalid diagnostic/telemetry JSON') from error


UINT = r'(?:0|[1-9][0-9]*)'
FIXED6 = r'[0-9]+\.[0-9]{6}'
FIXED3 = r'[0-9]+\.[0-9]{3}'
PATTERNS = {
    'scalar-frames': rf'functions=(?P<functions>{UINT}) static_bytes_saved=(?P<static_bytes_saved>{UINT}) seconds=(?P<seconds>{FIXED6})',
    'scalar-promotion': rf'slots=(?P<slots>{UINT}) removed_addresses=(?P<removed_addresses>{UINT}) rewritten=(?P<rewritten>{UINT}) seconds=(?P<seconds>{FIXED6}) removed_moves=(?P<removed_moves>{UINT})',
    'forwarding': rf'wrappers=(?P<wrappers>{UINT}) calls=(?P<calls>{UINT}) longest_chain=(?P<longest_chain>{UINT}) stage=(?P<stage>before-inline|final)',
    'cfg': rf'before=(?P<before>{UINT}) after=(?P<after>{UINT}) seconds=(?P<seconds>{FIXED6})',
    'export': rf'frontend_ms=(?P<frontend_ms>{FIXED3}) lowering_ms=(?P<lowering_ms>{FIXED3}) functions=(?P<functions>{UINT}) ops=(?P<ops>{UINT}) bytes=(?P<bytes>{UINT})',
}


def telemetry_line(raw):
    text = raw.decode('utf-8')
    if text.startswith('rust-interp-aggregate-frames: '):
        kind = 'aggregate-frames'
        value = parse_json(text.removeprefix('rust-interp-aggregate-frames: '))
        require(isinstance(value, dict) and set(value) == {'capture_seconds', 'declines', 'finalize_seconds',
                'functions', 'initialization_unchanged', 'static_bytes_saved'}, 'aggregate telemetry fields differ')
        require(value['initialization_unchanged'] is True, 'aggregate initialization contract differs')
        require(all(type(value[name]) is int and value[name] >= 0 for name in ('functions', 'static_bytes_saved')),
                'invalid aggregate integer counters')
        require(all(type(value[name]) in (int, float) and math.isfinite(value[name]) and value[name] >= 0
                    for name in ('capture_seconds', 'finalize_seconds')), 'invalid aggregate times')
        require(isinstance(value['declines'], dict) and all(isinstance(name, str) and name
                    and type(count) is int and count >= 0 for name, count in value['declines'].items()),
                'invalid aggregate decline counters')
        return kind, value
    for kind, pattern in PATTERNS.items():
        prefix = 'rust-interp-' + kind + ': '
        if text.startswith(prefix):
            match = re.fullmatch(pattern, text.removeprefix(prefix))
            require(match is not None, 'invalid known telemetry grammar: ' + kind)
            value = {key: token if key == 'stage' else float(token) if key in ('seconds', 'frontend_ms', 'lowering_ms')
                     else int(token) for key, token in match.groupdict().items()}
            require(all(not isinstance(item, float) or math.isfinite(item) for item in value.values()), 'nonfinite telemetry')
            return kind, value
    raise RuntimeError('unknown exporter stderr line')


def split_stderr(raw, *, allow_telemetry):
    """Retain every byte and line position; never normalize a compiler message."""
    require(isinstance(raw, bytes), 'raw stderr bytes required')
    segments, compiler, position = [], [], 0
    for line in raw.splitlines(keepends=True):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n'), 'complete LF-terminated stderr line required')
        body = line[:-1]
        segment = dict(start=position, end=position + len(line), raw_hex=line.hex())
        if body.startswith(b'{'):
            diagnostic = parse_json(body)
            require(isinstance(diagnostic, dict) and diagnostic.get('$message_type') == 'diagnostic'
                    and diagnostic.get('level') in ('error', 'warning', 'note', 'help', 'failure-note'),
                    'unrecognized compiler JSON line')
            segment.update(channel='compiler', diagnostic=diagnostic)
            compiler.append(line)
        else:
            require(allow_telemetry, 'telemetry/unstructured line in native or failing compiler output')
            kind, value = telemetry_line(body)
            segment.update(channel='telemetry', kind=kind, values=value)
        segments.append(segment); position += len(line)
    require(position == len(raw) and b''.join(bytes.fromhex(row['raw_hex']) for row in segments) == raw,
            'stderr separation was not lossless')
    return dict(raw_sha256=hashlib.sha256(raw).hexdigest(), raw_bytes=len(raw), segments=segments,
                compiler_stderr_hex=b''.join(compiler).hex())


def compare_compiler_stderr(native, exported):
    require(native['compiler_stderr_hex'] == exported['compiler_stderr_hex'], 'raw compiler diagnostic bytes differ')

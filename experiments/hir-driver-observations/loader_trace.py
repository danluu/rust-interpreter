"""Strict readback of the two real hash-driver processes, without executing one.

The caller must independently qualify the static provider closure and preserve
its bytes across execution. A dyld path alone is not provider qualification.
"""
import hashlib
import math
from pathlib import PurePosixPath
import re

import observations


MAX_BYTES = 2**20
UUID = r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}'


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(path):
    require(type(path) is str and path.startswith('/') and not path.startswith('//'),
            'absolute image path required')
    require(all(ord(char) >= 32 and ord(char) != 127 for char in path),
            'control character in image path')
    parsed = PurePosixPath(path)
    require(str(parsed) == path and '..' not in parsed.parts,
            'noncanonical image path')
    return path


def system_image(path):
    return path.startswith(('/usr/lib/', '/System/Library/'))


def parse(raw, *, pid, allowed_private):
    """Accept only the two observed dyld forms, exact PID and full private set.

    System images follow the separately declared macOS shared-cache assumption.
    A delayed-load note must refer to one earlier, unambiguous system image.
    Every other stderr line, including compiler diagnostics, rejects the run.
    """
    require(type(pid) is int and pid > 0, 'positive process PID required')
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and raw.endswith(b'\n'),
            'bounded complete loader stderr required')
    require(type(allowed_private) in (set, frozenset) and allowed_private,
            'explicit nonempty private provider set required')
    for path in allowed_private:
        canonical(path)
        require(not system_image(path), 'private allowlist contains a system image')
    prefix = rf'dyld\[{pid}\]: '
    loaded, basenames, events = set(), {}, []
    for number, line in enumerate(raw[:-1].split(b'\n'), 1):
        text = line.decode('utf-8', errors='strict')
        image = re.fullmatch(prefix + rf'(?:<({UUID})> +)?(/.+)', text)
        delayed = re.fullmatch(prefix + r'move loaded to delayed: ([^/\r\n]+)', text)
        if image:
            path = canonical(image[2])
            basenames.setdefault(PurePosixPath(path).name, set()).add(path)
            if not system_image(path):
                require(path in allowed_private, 'foreign private image: ' + path)
                loaded.add(path)
            event = dict(kind='image', path=path, uuid=image[1], system=system_image(path))
        elif delayed:
            matches = basenames.get(delayed[1], set())
            require(len(matches) == 1 and all(system_image(path) for path in matches),
                    'unproved or ambiguous delayed system image')
            event = dict(kind='delayed-system-image', path=next(iter(matches)))
        else:
            raise ValueError('unexpected loader stderr at line ' + str(number))
        events.append(dict(line=number, raw_sha256=hashlib.sha256(line + b'\n').hexdigest(), **event))
    require(loaded == allowed_private, 'missing private image from actual trace')
    return dict(status='validated-loader-observations-only', pid=pid,
                stderr_sha256=hashlib.sha256(raw).hexdigest(),
                loaded_non_system=sorted(loaded), events=events,
                system_images='declared macOS shared-cache assumption; not individually byte-qualified')


def process(receipt, stdout, stderr, *, command, cwd, environment, allowed_private):
    """Join raw semantics and actual loader PID to an owned_driver receipt.

    This is readback only. It does not replace source guards, process ownership,
    prior B3/native qualification, or the stage's complete command inventory.
    """
    require(type(command) is list and len(command) == 5 and command[-1] in ('serial', 'parallel'),
            'exact driver command required')
    for path in command[:4]:
        canonical(path)
    require(receipt['command'] == command and receipt['cwd'] == cwd
            and receipt['environment'] == environment, 'actual command context differs')
    require(environment.get('DYLD_PRINT_LIBRARIES') == '1', 'actual loader tracing required')
    require(receipt['status'] == 'passed' and receipt['errors'] == []
            and receipt['child_may_be_live'] is False and receipt['probe_may_be_live'] is False,
            'unsuccessful or unresolved owned driver')
    waited = receipt['wait']
    require(waited['status'] == 'exited' and type(waited['returncode']) is int
            and waited['returncode'] == 0 and waited['child_may_be_live'] is False,
            'driver did not exit successfully')
    events = receipt['events']
    require(events == waited['events'] and len(events) == 2
            and [event['kind'] for event in events] == ['started', 'terminal'],
            'driver underwent timeout or stop handling')
    require(all(type(event['elapsed']) in (int, float) and math.isfinite(event['elapsed'])
                and event['elapsed'] >= 0 for event in events)
            and events[0]['elapsed'] <= events[1]['elapsed'] < 120,
            'invalid driver elapsed-time record')
    require(all(events[0][key] == value for key, value in
                dict(timeout=120.0, grace=5.0, reap=5.0, interval=5.0).items())
            and events[1]['status'] == 'exited' and events[1]['returncode'] == 0
            and events[1]['reason'] is None and waited['reason'] is None
            and waited['errors'] == [], 'driver wait policy or terminal differs')
    require(receipt['mode'] == command[-1], 'receipt process mode differs')
    for name, raw in [('stdout', stdout), ('stderr', stderr)]:
        require(type(raw) is bytes and len(raw) <= MAX_BYTES, 'oversized process stream')
        require(hashlib.sha256(raw).hexdigest() == receipt[name + '_sha256'],
                'retained process stream differs')
    require(command[0] in allowed_private, 'actual driver executable missing from loader closure')
    parsed_stdout = observations.parse(stdout, mode=command[-1])
    parsed_stderr = parse(stderr, pid=receipt['pid'], allowed_private=allowed_private)
    return dict(status='validated-process-readback-only', mode=command[-1], pid=receipt['pid'],
                observations=parsed_stdout, loader=parsed_stderr)

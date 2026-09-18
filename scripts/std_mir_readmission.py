"""Readmit unchanged metadata after a volume device number changes.

The caller holds std-mir.lock. Historical ready manifests remain immutable.
Only a uniform device-number change is eligible; all other stamp differences
still fail. A separate receipt amortizes the complete content verification.
"""
import hashlib
import json
import os
import stat


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]


def file_digest(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def validate(work, ready, result):
    original = {name: item['stamp'] for name, item in result['artifacts'].items()}
    current = {}
    for name in original:
        path = work / name
        if not path.is_file():
            raise RuntimeError('standard-library MIR artifact changed: ' + str(path))
        current[name] = stamp(path.stat())
    if current == original:
        return
    # Do not turn a general artifact mutation into a cache miss or silently repair it.
    old_devices = {s[0] for s in original.values()}
    new_devices = {s[0] for s in current.values()}
    if (len(old_devices) != 1 or len(new_devices) != 1 or old_devices == new_devices
            or any(current[name][1:] != before[1:] for name, before in original.items())):
        raise RuntimeError('standard-library MIR artifact changed beyond device identity')
    ready_hash = hashlib.sha256(ready.read_bytes()).hexdigest()
    receipt = work / ('readmission-' + ready_hash + '-' + str(next(iter(new_devices))) + '.json')
    expected = dict(schema_version=1, owner=result['owner'], ready_sha256=ready_hash,
                    old_devices=sorted(old_devices), new_devices=sorted(new_devices),
                    artifacts={name: dict(sha256=result['artifacts'][name]['sha256'], stamp=value)
                               for name, value in current.items()})
    if receipt.exists():
        if json.loads(receipt.read_text()) != expected:
            raise RuntimeError('standard-library MIR readmission receipt changed')
        return
    for name, before in current.items():
        path = work / name
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or stamp(opened) != before:
                raise RuntimeError('standard-library MIR artifact changed during readmission')
            digest = file_digest(stream)
            if stamp(os.fstat(stream.fileno())) != before:
                raise RuntimeError('standard-library MIR artifact changed during readmission')
        if digest != result['artifacts'][name]['sha256']:
            raise RuntimeError('standard-library MIR content changed: ' + str(path))
    if any(stamp((work / name).stat()) != value for name, value in current.items()):
        raise RuntimeError('standard-library MIR artifact changed during readmission')
    if hashlib.sha256(ready.read_bytes()).hexdigest() != ready_hash:
        raise RuntimeError('standard-library MIR manifest changed during readmission')
    temporary = receipt.with_suffix('.tmp')
    with temporary.open('x') as stream:
        stream.write(json.dumps(expected, indent=2) + '\n')
    temporary.replace(receipt)

#!/usr/bin/env python3
"""One approved source-generation attempt and one separate verification attempt."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE = ROOT / 'experiments/hir-options-hash-packed-sidecars'
PYTHON = '/opt/homebrew/bin/python3'
SOURCES = {
    'contract.py': '0e446f42a85ef3d1ec5bdcae78f553aae1d8c32c93ef8a19c90eeaa4fc75474e',
    'generate.py': '3a03f7851f8097f2968c0184ca00916137cd73aa4609f781f8870e6fa77f2d20',
    'verify.py': 'c943f3500e610613719e4a28b438b6265d85e2f37f8bf5d4f885d9f7a9dac2b6',
    'bindings.json': '8afec96917ef1a22aeb9fcc4df9e0ff111878c2ac05b0f7d04a9de526bc24757',
    'README.md': '70a6b81ae3a945cde59f55376ef523de14fc5e3ac3ef7d546c9eb4bbe7fed249',
    'QUALIFICATION.md': '9eeaa94c9379a22717f369e1b8f039be6588ac7f2b75b7b5965a48b332ffd7b4',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ident(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def guard():
    for name, digest in SOURCES.items():
        assert sha((SOURCE / name).read_bytes()) == digest, name
    bindings = json.loads((SOURCE / 'bindings.json').read_bytes())
    records = []
    for group in ['fixed_files', 'current_files', 'packed_base_files', 'packed_candidate_files']:
        for key, row in bindings[group].items():
            p = Path(row['path'])
            before = p.lstat()
            assert stat.S_ISREG(before.st_mode) and p.resolve(strict=True) == p
            assert ident(before) == row['identity'] and before.st_size == row['size'] <= 4 * 1024 * 1024
            raw = p.read_bytes()
            assert ident(p.lstat()) == ident(before) and sha(raw) == row['sha256']
            records.append(dict(group=group, key=key, **row))
    assert len(records) == 79 and sum(row['size'] for row in records) == 4318376
    for path in bindings['absent_paths']:
        assert not os.path.lexists(path)
    return records


def run(stage, script):
    work = OWNER / ('.work/options-hash-packed-sidecars-' + stage + '-execution-01')
    assert not os.path.lexists(work)
    work.mkdir()
    record = dict(stage=stage, status='preflight', started_at=time.time(),
                  controller_pid=os.getpid(), controller_parent_pid=os.getppid(),
                  dispatcher=str(Path(__file__).resolve()),
                  dispatcher_sha256=sha(Path(__file__).read_bytes()),
                  source_hashes=SOURCES, observation_deadline_seconds=120,
                  process_signals=False, retries=0)
    command = [PYTHON, '-B', str(SOURCE / script)]
    environment = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                   'HOME': str(Path.home()), 'LANG': 'C', 'LC_ALL': 'C',
                   'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'}
    record.update(command=command, environment=environment, requested_cwd=str(ROOT))
    child = None
    try:
        before = guard()
        write(work / 'inputs-before.json', before)
        record['preflight_finished_at'] = time.time()
        if stage == 'generation':
            assert not os.path.lexists(SOURCE / 'artifacts-01')
        else:
            assert (SOURCE / 'artifacts-01/manifest.json').is_file()
            assert not os.path.lexists(SOURCE / 'source-verification-01.json')
        with (work / 'stdout').open('xb') as stdout, (work / 'stderr').open('xb') as stderr:
            record['popen_started_at'] = time.time()
            child = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, start_new_session=True, close_fds=True)
            record.update(pid=child.pid, parent_pid=os.getpid(), process_group=os.getpgid(child.pid),
                          session_id=os.getsid(child.pid),
                          identity_scope='Popen ownership and kernel process-group/session observation; no separate ps/cwd probe.')
            assert record['process_group'] == record['session_id'] == child.pid
            write(work / 'started.json', record)
            try:
                returncode = child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                record.update(status='observation-timeout-child-not-signaled', returncode=None)
                raise
            record.update(returncode=returncode, child_finished_observed_at=time.time())
        for name in ['stdout', 'stderr']:
            p = work / name
            assert p.stat().st_size <= 256 * 1024
            record[name] = dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
        after = guard()
        write(work / 'inputs-after.json', after)
        assert after == before
        assert returncode == 0
        record['status'] = 'passed-source-step'
    except BaseException as error:
        record['error'] = repr(error)
        if record['status'] != 'observation-timeout-child-not-signaled':
            record['status'] = 'retained-failure'
        raise
    finally:
        record['finished_observed_at'] = time.time()
        for name in ['stdout', 'stderr']:
            p = work / name
            if p.is_file() and p.stat().st_size <= 256 * 1024:
                record[name] = dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
        write(work / 'actual.json', record)
        print(json.dumps({'stage': stage, 'status': record['status'], 'record': str(work / 'actual.json'),
                          'sha256': sha((work / 'actual.json').read_bytes()),
                          'pid': record.get('pid'), 'returncode': record.get('returncode')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    assert sys.dont_write_bytecode and not sys.flags.optimize
    run('generation', 'generate.py')
    run('verification', 'verify.py')

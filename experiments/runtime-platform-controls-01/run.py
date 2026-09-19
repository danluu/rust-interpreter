"""Reviewed pure-control admission; existing supervisor and exact owned child."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[1]
SOURCE = HERE.with_name('runtime-application-admission')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
sys.path.insert(0, str(X / 'experiments/stable-cgu'))
import owned_stage as owned
WORK = OWNER / '.work/runtime-platform-controls-01'


def read(path):
    return json.loads(Path(path).read_bytes())


def stamp(path):
    s = path.lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def guard(freeze):
    for name, row in freeze['files'].items():
        path = Path(name)
        assert path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode)
        assert stamp(path) == row['stamp'] and owned.sha(path) == row['sha256'] and stamp(path) == row['stamp'], name
    for name, resolved in freeze['routes'].items():
        assert str(Path(name).resolve(strict=True)) == resolved, name


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    assert sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == OWNER
    assert owned.sha(HERE / 'inputs.json') == args.inputs_sha256
    freeze = read(HERE / 'inputs.json')
    assert str(Path(sys.executable).resolve(strict=True)) == freeze['python']
    assert {k: v for k, v in os.environ.items() if k != '__CF_USER_TEXT_ENCODING'} == freeze['environment']
    if '__CF_USER_TEXT_ENCODING' in os.environ:
        parts = os.environ['__CF_USER_TEXT_ENCODING'].split(':')
        assert len(parts) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', value) for value in parts)
        assert int(parts[0], 16 if parts[0].lower().startswith('0x') else 10) == os.getuid() == 501
    guard(freeze)
    assert not WORK.exists() and not WORK.is_symlink() and WORK.parent.resolve(strict=True) == WORK.parent
    WORK.mkdir()
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                   commands=[], compiler_calls=0, provider_probes=0, B3_compositions=0,
                   inputs_sha256=args.inputs_sha256)
    def save(): owned.write(WORK / 'receipt.json', receipt)
    save()
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK, 600) as fd:
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=owned.disk(OWNER, 16)); save()
            guard(freeze); (WORK / 'tmp').mkdir()
            environment = freeze['environment'] | {'TMPDIR': str(WORK / 'tmp')}
            try:
                owned.run(freeze['command'], cwd=SOURCE, env=environment, out=WORK / 'command',
                          capacity_root=OWNER, pass_fds=(fd,))
            finally:
                if (WORK / 'command/receipt.json').is_file():
                    path = WORK / 'command/receipt.json'
                    receipt['commands'] = [dict(path=str(path), sha256=owned.sha(path), pid=read(path).get('pid'))]
                    save()
            stderr = (WORK / 'command/stderr').read_text()
            names = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', stderr, re.M)
            assert sorted(names) == freeze['expected_names']
            assert re.search(r'^Ran 5 tests in [0-9.]+s\n\nOK\n$', stderr, re.M)
            assert not (WORK / 'command/stdout').read_bytes()
            result = read(WORK / 'result.json')
            assert result['status'] == 'passed' and result['tests_run'] == 5 and result['expected_names'] == freeze['expected_names']
            assert all(result[name] == 0 for name in ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls'])
            assert not list((WORK / 'tmp').iterdir()), 'synthetic fixture cleanup incomplete'
            total = 0
            for path in WORK.rglob('*'):
                assert not path.is_symlink()
                if path.is_file():
                    total += path.stat().st_size
                    assert path.stat().st_size <= 256 * 1024
                else:
                    assert path.is_dir()
            assert total <= 2 * 1024 * 1024, 'retained pure-control output cap exceeded'
            guard(freeze)
            receipt.update(status='passed', controls_passed=5, result_sha256=owned.sha(WORK / 'result.json'),
                           retained_file_bytes=total, free_bytes_after=owned.disk(OWNER, 9))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error)); raise
    finally:
        receipt['finished_at'] = time.time(); save()


if __name__ == '__main__':
    main()

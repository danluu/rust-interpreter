"""Archive one completed synthetic-control history, with exact member readback."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, workload_lock, require, write

WORK = ROOT / '.work/runtime-compiler-controls-archive-02'
INPUTS = ROOT / '.work/runtime-compiler-controls-archive-inputs-02.json'
RESULT = ROOT / 'results/runtime-compiler-controls-02'
CONTROLS = ROOT / '.work/runtime-compiler-controls-02'
OUTER = ROOT / '.work/experiments/runtime-compiler-controls-supervisor-02'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected):
    p = Path(path)
    require(p.is_file() and not p.is_symlink() and p.resolve() == p and p.is_relative_to(ROOT),
            'archive input is not an ordinary owned file')
    data = p.read_bytes()
    require(sha(data) == expected, 'archive input changed: ' + str(p))
    return data


def main():
    require(len(sys.argv) == 3 and sys.argv[1] == '--inputs-sha' and sys.dont_write_bytecode,
            'supply frozen input hash and python -B')
    raw = checked(INPUTS, sys.argv[2]); frozen = json.loads(raw)
    WORK.mkdir()
    record = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                  canonical_lock=str(CANONICAL_LOCK), lock_wait_seconds=600, inputs_sha256=sha(raw),
                  helper_sha256=sha(Path(__file__).read_bytes()))
    write(WORK / 'summary.json', record)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            record.update(status='running', admitted_at=time.time())
            write(WORK / 'summary.json', record)
            checked(INPUTS, sys.argv[2])
            for path, expected in frozen['source_guards'].items():
                checked(path, expected)
            payloads = {path: checked(path, row['sha256']) for path, row in frozen['files'].items()}
            require(all(len(payloads[p]) == row['size'] for p, row in frozen['files'].items()),
                    'archive input byte count differs')
            def read(path):
                return json.loads(payloads[str(path)])
            summary = read(CONTROLS / 'summary.json'); command = read(CONTROLS / 'command/receipt.json')
            outer = read(OUTER / 'status.json'); plan = read(CONTROLS / 'frozen-inputs.json')
            snapshots = read(CONTROLS / 'source-snapshots.json')
            require(sha(payloads[str(CONTROLS / 'frozen-inputs.json')]) == summary['frozen_inputs_sha256']
                    and sha(payloads[str(CONTROLS / 'source-snapshots.json')]) == summary['source_snapshots_sha256'],
                    'frozen input or snapshot manifest binding differs')
            require(summary['status'] == 'passed' and summary['tests'] == 14
                    and summary['source_revision'] == frozen['source_revision']
                    and command['status'] == 'finished' and command['returncode'] == 0
                    and outer['status'] == 'finished' and outer['returncode'] == 0,
                    'control history is not completely successful')
            require(outer['child_pid'] == summary['pid'] == command['supervisor_pid']
                    and outer['supervisor_pid'] == summary['parent_pid'] == command['parent_pid']
                    and outer['started_at'] <= summary['admitted_at'] <= command['started_at']
                    <= command['finished_at'] <= summary['finished_at'] <= outer['finished_at'],
                    'terminal process/time association differs')
            require(command['command'] == plan['command'] and command['cwd'] == str(ROOT)
                    and command['environment'] == summary['environment'], 'actual control invocation differs')
            for stream in ('stdout', 'stderr'):
                require(sha(payloads[str(CONTROLS / 'command' / stream)]) == command[stream + '_sha256'],
                        'raw command output differs')
            require(sha(payloads[str(CONTROLS / 'command/receipt.json')]) == summary['command_receipt_sha256']
                    and sha(payloads[str(OUTER / 'command.log')]) == outer['log_sha256']
                    and sha(payloads[str(OUTER / 'plan.json')]) == outer['plan_sha256'], 'raw receipts differ')
            raw_tests = payloads[str(CONTROLS / 'command/stderr')].decode()
            require(sorted(re.findall(r'^test_[^\n]* \(([^)]+)\) \.\.\. ok$', raw_tests, re.M))
                    == plan['required_tests'] and re.search(r'^Ran 14 tests in [\d.]+s$', raw_tests, re.M)
                    and re.search(r'^OK$', raw_tests, re.M), 'exact fourteen raw passes missing')
            require(set(snapshots) == set(plan['files']), 'source snapshot set differs')
            for origin, row in snapshots.items():
                require(sha(payloads[row['path']]) == row['sha256'] == plan['files'][origin],
                        'retained source snapshot differs')
            RESULT.mkdir(parents=True)
            manifest = {path: dict(member='files/' + str(index), sha256=sha(data), size=len(data))
                        for index, (path, data) in enumerate(sorted(payloads.items()))}
            manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
            archive = RESULT / 'evidence.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for name, data in [('manifest.json', manifest_bytes),
                                   *((manifest[p]['member'], b) for p, b in sorted(payloads.items()))]:
                    info = tarfile.TarInfo(name); info.size = len(data); info.mode = 0o444
                    tar.addfile(info, io.BytesIO(data))
            expected = {'manifest.json': sha(manifest_bytes), **{v['member']: v['sha256'] for v in manifest.values()}}
            with tarfile.open(archive, 'r:gz') as tar:
                members = tar.getmembers()
                require(len(members) == len(expected) and {m.name for m in members} == set(expected),
                        'archive membership differs')
                for member in members:
                    require(member.isfile() and sha(tar.extractfile(member).read()) == expected[member.name],
                            'archive member readback differs')
            for path, expected_sha in frozen['source_guards'].items():
                checked(path, expected_sha)
            for path, row in frozen['files'].items():
                checked(path, row['sha256'])
            (RESULT / 'manifest.json').write_bytes(manifest_bytes)
            record.update(status='passed', finished_at=time.time(), source_revision=frozen['source_revision'],
                tests=14, control_supervisor=outer['supervisor_pid'], control_helper=summary['pid'],
                control_child=command['pid'], archive_sha256=sha(archive.read_bytes()),
                archive_bytes=archive.stat().st_size, manifest_sha256=sha(manifest_bytes),
                files=len(manifest), members=len(members), source_snapshots=len(snapshots))
            write(RESULT / 'summary.json', record)
            write(WORK / 'summary.json', record)
    except BaseException as error:
        record.update(status='failed', error=repr(error), finished_at=time.time())
        write(WORK / 'summary.json', record)
        raise


if __name__ == '__main__':
    main()

"""Retain completed admission histories; no live compiler/provider payloads.

Source-only successor of archive_hir_options_preparation_03.py. Its exact
freeze is intentionally absent until review. No compiler, metadata probe,
test, process-control operation or source mutation is performed here.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import time

X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
F = X / '.work/hir-options-admission-evidence-inputs-01.json'
W = X / '.work/hir-options-admission-evidence-retention-01'
OUT = X / 'results/hir-options-hash-admission-01'
OWNED = X / 'experiments/stable-cgu/owned_stage.py'
MIB = 2**20
LIMITS = dict(files=4096, file_bytes=96*MIB, logical_bytes=512*MIB,
              unique_bytes=256*MIB, archive_bytes=128*MIB, expanded_bytes=288*MIB,
              manifest_bytes=8*MIB, reservation_bytes=192*MIB)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]


def capture(path, row):
    path = Path(path)
    before = stamp(path)
    require(path.resolve(strict=True) == path and stat.S_ISREG(before[2])
            and before[3] <= LIMITS['file_bytes'] and before == row['stamp'], 'ordinary bounded exact proof required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        s = os.fstat(stream.fileno())
        require([s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink] == before,
                'proof replaced before descriptor read')
        data = stream.read(LIMITS['file_bytes'] + 1)
        s = os.fstat(stream.fileno())
        require([s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink] == before,
                'proof changed during descriptor read')
    require(stamp(path) == before and len(data) == row['bytes'] and digest(data) == row['sha256'],
            'proof bytes/size/identity changed')
    return data


def membership(root):
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'ordinary completed evidence directory required')
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(parent) / name
            info = path.lstat()
            require(not stat.S_ISLNK(info.st_mode), 'evidence symlink is not archive payload')
            if stat.S_ISDIR(info.st_mode):
                continue
            require(stat.S_ISREG(info.st_mode), 'special evidence file')
            result.append(str(path))
    return sorted(result)


class CappedArchive:
    """Enforce the compressed output ceiling before each physical write."""
    def __init__(self, stream, guard):
        self.stream, self.guard = stream, guard
    def write(self, data):
        self.guard()
        require(self.stream.tell() + len(data) <= LIMITS['archive_bytes'], 'compressed archive write bound exceeded')
        return self.stream.write(data)
    def flush(self):
        return self.stream.flush()
    def tell(self):
        return self.stream.tell()


def verify_history(freeze, payloads):
    def raw(path):
        require(str(path) in payloads, 'missing exact retained proof: ' + str(path))
        return payloads[str(path)]
    def value(path):
        return json.loads(raw(path))
    def hashof(path):
        return digest(raw(path))
    actual = []
    for item in freeze['stages']:
        work = Path(item['work']); terminal = value(work / 'receipt.json')
        require(terminal['status'] == item['status'] and len(terminal['commands']) == item['children'], 'stage terminal differs')
        original_freeze = value(item['inputs'])
        launch = value(item['launch'])
        require(launch['inputs_sha256'] == hashof(item['inputs']), 'actual launch/input freeze differs')
        recorded = value(item['actual'])
        require(recorded['launch'] == item['launch'] and recorded['launch_sha256'] == hashof(item['launch'])
                and recorded['command'] == launch['command'] and recorded['environment'] == launch['environment']
                and recorded['cwd'] == str(X), 'original launch association differs')
        for stream in ['stdout', 'stderr']:
            require(recorded[stream] in payloads, 'original launcher raw stream omitted')
        outer = Path(item['outer']); outer_status = value(outer / 'status.json'); outer_plan = value(outer / 'plan.json')
        announcement = value(recorded['stdout'])
        require(not raw(recorded['stderr']) and announcement['supervisor_pid'] == outer_status['supervisor_pid']
                and announcement['directory'] == str(outer), 'actual launcher announcement differs')
        identity = announcement['identity'].splitlines()
        require(len(identity) == 2 and identity[1].split()[:2] == [str(outer_status['supervisor_pid']), str(recorded['supervisor_launcher_pid'])],
                'actual launcher/supervisor parent association differs')
        command = launch['command']; require(command.count('--') == 1, 'original supervisor boundary differs')
        require(outer_status['status'] == 'finished' and outer_status['returncode'] == item['outer_returncode']
                and outer_status['child_pid'] == terminal['pid'] and outer_status['supervisor_pid'] == terminal['parent_pid']
                and outer_status['command'] == outer_plan['command'] == command[command.index('--') + 1:]
                and outer_status['cwd'] == outer_plan['owner'] == str(X)
                and outer_status['plan_sha256'] == hashof(outer / 'plan.json')
                and outer_status['log_sha256'] == hashof(outer / 'command.log')
                and recorded['started_at'] <= outer_status['started_at'] <= terminal['started_at'] <= terminal['admitted_at']
                <= terminal['finished_at'] <= outer_status['finished_at'], 'supervisor/terminal association differs')
        if item['kind'] == 'parser-controls':
            rows = [dict(argv=original_freeze['command'], cwd=item['cwd'], environment=original_freeze['environment'] | {'TMPDIR': str(work / 'tmp')})]
            require(terminal['controls_passed'] == 9, 'nine parser controls required')
        else:
            plan = value(item['plan'])
            require(original_freeze['plan_sha256'] == hashof(item['plan']), 'actual stage plan/freeze differs')
            rows = plan['children'][:item['children']]
        previous = terminal['admitted_at']
        for index, (ref, wanted) in enumerate(zip(terminal['commands'], rows, strict=True)):
            child = value(ref['path']); expected_status, expected_code = item['child_results'][index]
            require(hashof(ref['path']) == ref['sha256'] and child['pid'] == ref['pid']
                    and child['status'] == expected_status and child['returncode'] == expected_code
                    and child['command'] == wanted['argv'] and ('command' not in ref or ref['command'] == wanted['argv'])
                    and child['cwd'] == wanted['cwd'] and child['environment'] == wanted['environment']
                    and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid']
                    and previous <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                    'actual child argv/env/process/status association differs')
            previous = child['finished_at']
            for stream in ['stdout', 'stderr']:
                require(hashof(Path(ref['path']).parent / stream) == child[stream + '_sha256'], 'actual raw stream differs')
            if 'expected_returncode' in wanted:
                require(expected_code == wanted['expected_returncode'] and ref['label'] == wanted['label'], 'negative-control expectation differs')
            elif item['kind'] != 'build-failure':
                require(expected_code in wanted.get('expected', [0]), 'declared metadata/control status differs')
        if item['kind'] == 'metadata-failure':
            require(terminal['compiler_builds'] == 0 and terminal['error'] == "RuntimeError('unknown linker architecture grammar')"
                    and len(plan['children']) == 50, 'original metadata failure changed')
        elif item['kind'] == 'metadata-continuation':
            require(terminal['compiler_builds'] == 0 and terminal['saved_children'] == 48
                    and terminal['prior_receipt_sha256'] == hashof(X / '.work/hir-options-hash-compiler-metadata-03/receipt.json'),
                    'continuation changed original failed admission')
            metadata = value(work / 'metadata.json')
            require(terminal['metadata_sha256'] == hashof(work / 'metadata.json')
                    and metadata['status'] == 'metadata-qualified-not-built' and metadata['prior_children'] == 48
                    and metadata['continuation_children'] == 2, 'actual metadata qualification differs')
        elif item['kind'] == 'build-failure':
            require(terminal['compiler_stages_completed'] == 0 and not terminal['native_recipe_qualified']
                    and not terminal['hash_driver_qualified'] and not terminal['application_qualified'],
                    'failed bootstrap attempt cannot qualify compiler')
            stderr = raw(Path(terminal['commands'][-1]['path']).parent / 'stderr')
            require(b'current package believes it\'s in a workspace when it\'s not' in stderr,
                    'retained workspace-membership failure missing')
        elif item['kind'] == 'parser-controls':
            stderr = raw(Path(terminal['commands'][0]['path']).parent / 'stderr').decode()
            names = re.findall(r'(?m)^(test_[A-Za-z0-9_]+) \([^\n]+\) \.\.\. ok$', stderr)
            require(len(names) == len(set(names)) == 9 and sorted(names) == sorted(original_freeze['expected_names'])
                    and re.search(r'Ran 9 tests in [0-9.]+s\n\nOK\n$', stderr), 'actual parser test results differ')
        elif item['kind'] == 'workspace-controls':
            controls = value(work / 'controls.json')
            require(terminal['controls_passed'] == 6 and terminal['compiler_builds'] == 0
                    and terminal['controls_sha256'] == hashof(work / 'controls.json')
                    and controls['status'] == 'passed' and controls['compiler_builds'] == 0 and controls['metadata_commands'] == 6,
                    'actual workspace controls differ')
            for row, ref, wanted in zip(controls['rows'], terminal['commands'], plan['children'], strict=True):
                child = value(ref['path'])
                require(row['label'] == wanted['label'] and row['expected_returncode'] == child['returncode']
                        and all(row[stream + '_sha256'] == child[stream + '_sha256'] for stream in ['stdout', 'stderr']),
                        'workspace result/raw mapping differs')
            require(controls['rows'][0]['result'] == controls['rows'][2]['result'], 'outer workspace changed')
        for audit_ref in item['audits']:
            audit = value(audit_ref['path'])
            require(audit['status'] == audit_ref['status'] and audit[audit_ref['receipt_field']] == hashof(work / 'receipt.json'),
                    'independent actual audit association differs')
        actual.append(dict(kind=item['kind'], status=item['status'], children=item['children'],
                           receipt_sha256=hashof(work / 'receipt.json'), child_results=item['child_results']))
    require(sum(item['children'] for item in actual) == 60, 'exact completed sixty-child history required')
    historical = freeze['historical_parent_manifest']
    old_inputs = value(X / 'experiments/hir-options-hash/workspace-controls-01/inputs.json')
    require(old_inputs['files'][str(X / 'Cargo.toml')]['sha256'] == historical['sha256']
            and hashof(historical['preserved_path']) == historical['sha256'], 'historical parent manifest binding differs')
    return actual


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--inputs-sha256', required=True); args = parser.parse_args()
    require(Path.cwd() == X and sys.dont_write_bytecode and not sys.flags.optimize and sha(F) == args.inputs_sha256,
            'exact owner/Python/freeze required')
    initial_stamp = stamp(F); freeze_bytes = F.read_bytes(); freeze = json.loads(freeze_bytes)
    require(freeze['owner'] == str(X) and freeze['limits'] == LIMITS, 'retention scope/bounds differ')
    require(sha(Path(sys.executable).resolve(strict=True)) == freeze['python']['sha256']
            and stamp(Path(sys.executable).resolve(strict=True)) == freeze['python']['stamp'], 'retention Python changed')
    expected = freeze['environment']; observed = dict(os.environ); extra = set(observed) - set(expected)
    require(all(observed.get(k) == v for k, v in expected.items()) and extra <= {'__CF_USER_TEXT_ENCODING'}, 'retention environment differs')
    if extra:
        cf = observed['__CF_USER_TEXT_ENCODING'].split(':')
        require(len(cf) == 3 and all(re.fullmatch(r'(?:0[xX][0-9a-fA-F]{1,8}|[0-9]{1,10})', v) for v in cf)
                and int(cf[0], 16 if cf[0].lower().startswith('0x') else 10) == os.getuid() == 501, 'unexpected Darwin CF context')
    capture(OWNED, freeze['files'][str(OWNED)])
    capture(Path(__file__).resolve(), freeze['files'][str(Path(__file__).resolve())])
    spec = importlib.util.spec_from_file_location('admission_archive_owned', OWNED)
    owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
    W.mkdir(exist_ok=False)
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                   inputs_sha256=args.inputs_sha256, metadata_probes_rerun=0, compiler_builds=0, tests_rerun=0)
    owned.write(W / 'receipt.json', receipt)
    try:
        with owned.workload_lock(owned.CANONICAL_LOCK, 600):
            free = owned.disk(X, 9); require(free >= 9*2**30 + LIMITS['reservation_bytes'], 'archive reservation unavailable')
            receipt.update(status='running', admitted_at=time.time(), free_bytes_before=free); owned.write(W / 'receipt.json', receipt)
            payloads, unique = {}, {}
            for name, row in freeze['files'].items():
                owned.disk(X, 9); data = capture(name, row); payloads[name] = unique.setdefault((row['sha256'], len(data)), data)
            require(len(payloads) <= LIMITS['files'] and sum(map(len, payloads.values())) == freeze['logical_bytes'] <= LIMITS['logical_bytes']
                    and sum(map(len, unique.values())) == freeze['unique_bytes'] <= LIMITS['unique_bytes'], 'archive input bounds differ')
            for directory, members in freeze['directories'].items():
                require(membership(directory) == members, 'completed evidence membership changed')
            for name in freeze['absent_paths']:
                require(not Path(name).exists() and not Path(name).is_symlink(), 'closed control created a target')
            prior = freeze['prior_archive']
            require(stamp(Path(prior['path'])) == prior['stamp'] and sha(prior['path']) == prior['sha256'], 'prior retained preparation archive differs')
            actual = verify_history(freeze, payloads)
            require(stamp(F) == initial_stamp and sha(F) == args.inputs_sha256, 'retention freeze changed')
            payloads[str(F)] = freeze_bytes
            require(len(payloads) <= LIMITS['files'] and sum(map(len, payloads.values())) <= LIMITS['logical_bytes']
                    and sum(map(len, unique.values())) + len(freeze_bytes) <= LIMITS['unique_bytes'], 'freeze exceeded archive input budget')
            if not OUT.parent.exists():
                OUT.parent.mkdir()
            require(not OUT.exists() and not OUT.is_symlink() and OUT.parent.resolve(strict=True) == OUT.parent
                    and OUT.parent.is_dir(), 'fresh ordinary result directory required')
            OUT.mkdir()
            archive = OUT / 'evidence.tar.gz'; manifest = {}; first = {}
            with archive.open('xb') as file:
                with gzip.GzipFile(fileobj=CappedArchive(file, lambda: owned.disk(X, 9)), mode='wb', filename='', mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode='w') as tar:
                        for path, data in sorted(payloads.items()):
                            owned.disk(X, 9); name = path.lstrip('/'); key = (digest(data), len(data))
                            member = tarfile.TarInfo(name); member.mode = 0o644
                            if key in first:
                                member.type, member.linkname = tarfile.LNKTYPE, first[key]; tar.addfile(member)
                            else:
                                member.size = len(data); tar.addfile(member, io.BytesIO(data)); first[key] = name
                            manifest[name] = dict(source=path, sha256=key[0], bytes=key[1])
                    compressed.flush()
                file.flush(); os.fsync(file.fileno())
            require(archive.stat().st_size <= LIMITS['archive_bytes'], 'compressed archive bound exceeded')
            seen = set()
            with tarfile.open(archive, 'r:gz') as tar:
                for member in tar:
                    owned.disk(X, 9)
                    require(member.name in manifest and member.name not in seen and (member.isfile() or member.islnk()), 'unexpected archive member')
                    if member.islnk(): require(member.linkname in seen, 'missing/forward dedup link')
                    data = tar.extractfile(member).read(); row = manifest[member.name]
                    require(len(data) == row['bytes'] and digest(data) == row['sha256'], 'archive full-member readback differs')
                    seen.add(member.name)
            require(seen == set(manifest), 'incomplete archive readback')
            expanded = 0
            with gzip.open(archive, 'rb') as compressed:
                while block := compressed.read(MIB):
                    owned.disk(X, 9); expanded += len(block)
                    require(expanded <= LIMITS['expanded_bytes'], 'gzip framing expansion bound exceeded')
            # Full EOF verifies the complete gzip trailer/CRC beyond tar EOF.
            for name, row in freeze['files'].items():
                owned.disk(X, 9); require(capture(name, row) == payloads[name], 'proof changed during retention')
            for directory, members in freeze['directories'].items():
                require(membership(directory) == members, 'completed evidence membership changed during retention')
            for name in freeze['absent_paths']:
                require(not Path(name).exists() and not Path(name).is_symlink(), 'closed control target appeared during retention')
            require(stamp(F) == initial_stamp and sha(F) == args.inputs_sha256 and dict(os.environ) == observed,
                    'freeze/environment changed during retention')
            require(stamp(Path(prior['path'])) == prior['stamp'] and sha(prior['path']) == prior['sha256'], 'prior archive changed')
            result = dict(schema_version=1, files=manifest, stages=actual, archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                logical_bytes=sum(row['bytes'] for row in manifest.values()), physical_payloads=len(first), expanded_bytes=expanded,
                full_member_readback=True, gzip_eof_crc=True, prior_preparation_archive=prior,
                scope='Completed metadata failure and continuation, parser controls, failed bootstrap attempt, and workspace controls. Frozen catalogs and raw histories retained; live compiler/SDK/registry/provider binaries excluded. Build02 and later B3/runtime/application work are outside this archive.',
                metadata_qualified=True, compiler_qualified=False, application_qualified=False, performance_target_met=False,
                metadata_failure_preserved=True, compiler_build_failure_preserved=True, actual_workloads_rerun=False)
            require(len(json.dumps(result).encode()) <= LIMITS['manifest_bytes'], 'manifest bound exceeded')
            owned.write(OUT / 'manifest.json', result)
            receipt.update(status='passed', manifest_sha256=sha(OUT / 'manifest.json'), archive_sha256=sha(archive),
                archive_bytes=archive.stat().st_size, logical_members=len(manifest), full_member_readback=True,
                gzip_eof_crc=True, free_bytes_after=owned.disk(X, 9))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error)); raise
    finally:
        receipt['finished_at'] = time.time(); owned.write(W / 'receipt.json', receipt)


if __name__ == '__main__':
    main()

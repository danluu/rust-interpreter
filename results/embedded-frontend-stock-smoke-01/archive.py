#!/usr/bin/env python3
"""Archive only completed embedded-bootstrap evidence; never read B/runtime binaries."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
OWNER = Path('/Users/danluu/dev/rust-interp-embedded-frontend-bootstrap-20260913')
INPUTS = HERE / 'inputs.json'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def read(path, expected=None):
    data = Path(path).read_bytes()
    require(expected is None or digest(data) == expected, 'changed metadata: ' + str(path))
    return json.loads(data)


class Archive:
    def __init__(self, args):
        self.args = args
        require(digest(INPUTS.read_bytes()) == args.inputs_sha
                and digest(Path(__file__).read_bytes()) == args.helper_sha, 'archive source changed')
        self.inputs = read(INPUTS)
        require(self.inputs['policy'] == 'embedded-stock-smoke-archive-v1'
                and self.inputs['owner'] == str(OWNER) and not self.inputs['benchmark'], 'wrong archive scope')
        self.frozen = read(self.inputs['frozen']['path'], self.inputs['frozen']['sha256'])
        self.allowed = set(self.frozen['files']) | {str(INPUTS), str(Path(__file__).resolve())}
        self.allowed.add(self.inputs['native_source']['path'])
        self.allowed.update(x['path'] for x in self.inputs['extra_files'])
        self.allowed.add(self.inputs['frozen']['path'])
        self.allowed.add(self.inputs['readme']['path'])
        self.roots = [Path(p) for p in self.inputs['roots']]
        require(all(p.is_relative_to(OWNER / '.work') for p in self.roots), 'archive roots outside owned work')
        owned_path = OWNER / 'experiments/stable-cgu/owned_stage.py'
        require(digest(owned_path.read_bytes()) == self.frozen['files'][str(owned_path)], 'owned helper changed')
        spec = importlib.util.spec_from_file_location('embedded_archive_owned', owned_path)
        self.owned = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.owned
        spec.loader.exec_module(self.owned)
        require(str(self.owned.CANONICAL_LOCK) == self.inputs['canonical_lock'], 'wrong canonical lock')
        self.work = Path(self.inputs['work'])
        self.work.mkdir(exist_ok=False)
        self.result = Path(self.inputs['result'])
        self.excluded_root = Path(self.inputs['excluded_binary_subtree'])
        self.payloads, self.files = {}, {}
        self.record = dict(schema_version=1, policy=self.inputs['policy'], status='waiting',
            owner=str(OWNER), pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
            command=sys.argv, cwd=os.getcwd(), canonical_lock=str(self.owned.CANONICAL_LOCK), wait_seconds=600,
            helper_sha256=args.helper_sha, inputs_sha256=args.inputs_sha, benchmark=False,
            compiler_commands=0, deletions=0, live_runtime_binary_reads=0)
        self.save()

    def save(self):
        self.owned.write(self.work / 'receipt.json', self.record)

    def source_guard(self):
        require(digest(INPUTS.read_bytes()) == self.args.inputs_sha
                and digest(Path(__file__).read_bytes()) == self.args.helper_sha, 'archive source changed')
        require(str(Path(sys.executable).resolve()) == self.frozen['python']['resolved']
                and digest(Path(sys.executable).read_bytes()) == self.frozen['python']['sha256'], 'Python changed')

    def add(self, path, expected=None):
        path = Path(path)
        require(str(path) in self.allowed or any(path.is_relative_to(root) for root in self.roots),
                'path outside exact evidence scope: ' + str(path))
        require(not path.is_relative_to(self.excluded_root), 'native artifact payload must stay excluded')
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and path.resolve() == path, 'ordinary evidence required: ' + str(path))
        data = path.read_bytes()
        after = path.lstat()
        fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(fields(before) == fields(after) and len(data) == after.st_size, 'evidence changed during read')
        actual = digest(data)
        require(expected is None or actual == expected, 'evidence hash mismatch: ' + str(path))
        require(data[:4] not in [b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe',
                                b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'!<ar']
                and not data.startswith((b'\x1f\x8b', b'\xfd7zXZ', b'PK\x03\x04')),
                'binary/archive payload entered metadata scope: ' + str(path))
        require(str(path) not in self.files or self.files[str(path)]['sha256'] == actual,
                'same evidence path changed across checks')
        self.payloads.setdefault(actual, data)
        self.files[str(path)] = dict(sha256=actual, bytes=len(data), mode=stat.S_IMODE(after.st_mode), member='files/' + actual)
        return data

    def json(self, path, expected=None):
        return json.loads(self.add(path, expected))

    def tree(self, root):
        require(root.is_dir() and not root.is_symlink(), 'ordinary evidence root required')
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in list(dirs):
                path = Path(parent) / name
                if path == self.excluded_root:
                    dirs.remove(name)
                else:
                    require(not path.is_symlink(), 'symlink directory in evidence')
            for name in sorted(files):
                self.add(Path(parent) / name)

    def history(self, row):
        record = self.json(row['record']['path'], row['record']['sha256'])
        outer = self.json(row['supervisor']['path'], row['supervisor']['sha256'])
        require(record['status'] == row['status'] and record['pid'] == row['pid']
                and record['parent_pid'] == row['parent_pid'] and outer['status'] == 'finished'
                and outer['child_pid'] == row['pid'] and outer['supervisor_pid'] == row['parent_pid']
                and outer['returncode'] == (1 if row['status'] == 'failed' else 0), 'terminal process association changed')
        self.add(Path(row['supervisor']['path']).parent / 'command.log', outer['log_sha256'])
        if row['commands'] is not None:
            require(len(record['commands']) == row['commands'], 'actual command count differs')
            for index, item in enumerate(record['commands']):
                path = Path(item['path'])
                require(path == Path(row['record']['path']).parent / 'commands' / f'{index:03}' / 'receipt.json',
                        'command path/order differs')
                child = self.json(path, item['sha256'])
                require(child['command'] == item['command'] and child['returncode'] == item['returncode'],
                        'raw child association differs')
                schema = row['command_receipt_schema']
                require(schema in ['workflow_io', 'owned_stage'], 'unreviewed child receipt schema')
                for stream in ['stdout', 'stderr']:
                    key = stream + '_sha256'
                    if schema == 'workflow_io':
                        require(key not in child and key in item, 'inspection stream binding schema changed')
                        expected = item[key]
                    else:
                        require(key in child and (key not in item or item[key] == child[key]),
                                'owned child stream binding schema changed')
                        expected = child[key]
                    self.add(path.parent / stream, expected)
        if row['tests'] is not None:
            if 'tests' in record:
                require(record['tests'] == row['tests'], 'control count differs')
                root = Path(row['record']['path']).parent
                child = self.json(root / 'command/receipt.json', record['command_receipt_sha256'])
                require(child['returncode'] == 0, 'control child did not pass')
                self.add(root / 'command/stdout', child['stdout_sha256'])
                self.add(root / 'command/stderr', child['stderr_sha256'])
                snapshots = self.json(root / 'source-snapshots.json', record['source_snapshots_sha256'])
                for original, snapshot in snapshots.items():
                    require(snapshot['path'] == str(root / 'sources' / original.lstrip('/')), 'control snapshot path differs')
                    self.add(snapshot['path'], snapshot['sha256'])
                self.record.setdefault('control_snapshot_maps', []).append(dict(path=str(root / 'source-snapshots.json'), entries=len(snapshots)))
            else:
                require(record['controls'] == row['tests'] and record['saved_commands'] == 215
                        and record['saved_fresh_rows'] == 183, 'saved Cargo parser controls differ')
                root = Path(row['record']['path']).parent
                self.add(root / 'all-saved-rows.json', record['parsed_rows_sha256'])
                for original, expected in record['source_hashes'].items():
                    self.add(root / 'sources' / original.lstrip('/'), expected)
        return record

    def execute(self):
        try:
            with self.owned.workload_lock(self.owned.CANONICAL_LOCK, 600):
                self.record.update(status='running', admitted_at=time.time(), free_bytes_before=self.owned.disk(OWNER)); self.save()
                self.source_guard()
                prior = self.inputs['prior_archive_failure']
                require(self.json(prior['receipt']['path'], prior['receipt']['sha256'])['error'] == prior['error'],
                        'archive01 failure changed')
                for key in ['helper', 'inputs', 'launch']:
                    self.add(prior[key]['path'], prior[key]['sha256'])
                self.add(INPUTS, self.args.inputs_sha); self.add(Path(__file__).resolve(), self.args.helper_sha)
                self.add(self.inputs['readme']['path'], self.inputs['readme']['sha256'])
                self.add(self.inputs['frozen']['path'], self.inputs['frozen']['sha256'])
                for path, expected in self.frozen['files'].items():
                    self.add(path, expected)
                for item in self.inputs['extra_files']:
                    self.add(item['path'], item['sha256'])
                histories = [self.history(row) for row in self.inputs['anchors']]
                for root in self.roots:
                    self.tree(root)
                for item in self.inputs['proof_maps']:
                    mapping = self.json(item['path'], item['sha256'])
                    for versions in mapping.values():
                        for expected, row in versions.items():
                            require(expected == row['sha256'], 'historical proof key differs')
                            require(len(self.add(row['copy'], expected)) == row['bytes'], 'historical proof size differs')
                plan = self.json(self.inputs['plan']['path'], self.inputs['plan']['sha256'])
                for path, expected in plan['input_snapshots'].items():
                    self.add(path, expected)
                copies = self.json(self.inputs['composition_proofs']['path'], self.inputs['composition_proofs']['sha256'])
                require(len(copies) == 792 and len(plan['composition']['files']) == 334
                        and len(plan['composition']['private']) == 256, 'complete assembly counts differ')
                for row in copies:
                    require(row['copy']['sha256'] == row['original']['sha256'], 'composition proof copy differs')
                    require(len(self.add(row['copy']['path'], row['copy']['sha256'])) == row['copy']['size'], 'composition proof size differs')
                smoke = histories[-1]
                require(smoke['status'] == 'passed' and smoke['policy'] == 'embedded-frontend-stock-smoke-v1'
                        and smoke['source_unchanged'] and smoke['runtime_unchanged'] and smoke['source_restored']
                        and smoke['checks'] == dict(actual_hit=True, cold_capture=True, ordinary_output=True,
                            restored=True, uncalled_error_hit=True, uncalled_error_raw_equal=True)
                        and sum(x['role'] == 'smoke-control' for x in smoke['commands']) == 18, 'complete smoke qualification differs')
                self.add(self.inputs['native_source']['path'], self.inputs['native_source']['sha256'])
                stage = Path(self.inputs['anchors'][-1]['record']['path']).parent
                require(self.add(stage / 'original.rs') == self.add(stage / 'restored.rs'), 'fixture restoration differs')
                require(self.add(stage / 'commands/018/stderr') == self.add(stage / 'commands/019/stderr'), 'raw error equality differs')
                for item in smoke['native_executions']:
                    require(self.add(Path(item['receipt']).parent / 'stdout') == b'42\n', 'native execution differs')
                excluded = [dict(path=smoke['smoke']['path'], sha256=smoke['smoke']['sha256'], reason='stock compiler binary retained locally')]
                for item in smoke['native_executions']:
                    excluded.append(dict(path=item['snapshot'], sha256=item['snapshot_sha256'], reason='native fixture binary retained locally'))
                for path, expected in smoke['evidence_files'].items():
                    if Path(path).is_relative_to(self.excluded_root):
                        require(any(x['path'] == path and x['sha256'] == expected for x in excluded), 'unaccounted binary exclusion')
                    else:
                        self.add(path, expected)
                self.source_guard()
                manifest = dict(schema_version=1, policy=self.inputs['policy'], files=dict(sorted(self.files.items())),
                    excluded_binary_payloads=excluded, binary_policy=self.inputs['binary_policy'],
                    composition_files=334, private_files=256, beta_files=78, copied_proofs=792,
                    history_anchors=self.inputs['anchors'], smoke_checks=smoke['checks'], benchmark=False)
                manifest_bytes = encode(manifest)
                self.result.mkdir(parents=True, exist_ok=False)
                archive_path = self.result / 'evidence.tar.gz'
                with tarfile.open(archive_path, 'w:gz', compresslevel=1) as archive:
                    for name, data in [('manifest.json', manifest_bytes)] + [('files/' + h, b) for h, b in sorted(self.payloads.items())]:
                        self.owned.disk(OWNER)
                        member = tarfile.TarInfo(name); member.size = len(data); member.mode = 0o444; member.mtime = 0
                        archive.addfile(member, io.BytesIO(data))
                expected_members = {'manifest.json': digest(manifest_bytes)} | {'files/' + h: h for h in self.payloads}
                with tarfile.open(archive_path, 'r:gz') as archive:
                    members = archive.getmembers()
                    require(len(members) == len(expected_members) and {m.name for m in members} == set(expected_members), 'archive membership differs')
                    for member in members:
                        self.owned.disk(OWNER)
                        require(member.isfile() and digest(archive.extractfile(member).read()) == expected_members[member.name], 'archive readback differs')
                self.source_guard()
                (self.result / 'manifest.json').write_bytes(manifest_bytes)
                (self.result / 'archive.py').write_bytes(Path(__file__).read_bytes())
                (self.result / 'inputs.json').write_bytes(INPUTS.read_bytes())
                (self.result / 'README.md').write_bytes(self.add(self.inputs['readme']['path'], self.inputs['readme']['sha256']))
                self.record.update(status='passed', finished_at=time.time(), free_bytes_after=self.owned.disk(OWNER),
                    archive_path=str(archive_path), archive_sha256=digest(archive_path.read_bytes()), archive_bytes=archive_path.stat().st_size,
                    manifest_sha256=digest(manifest_bytes), verified_members=len(expected_members), file_paths=len(self.files),
                    unique_payloads=len(self.payloads), payload_bytes=sum(map(len, self.payloads.values())), excluded_binary_payloads=excluded,
                    smoke_receipt_sha256=self.inputs['anchors'][-1]['record']['sha256'], histories=len(histories))
                self.save(); self.owned.write(self.result / 'summary.json', self.record)
        except BaseException as error:
            self.record.update(status='failed', finished_at=time.time(), error=repr(error)); self.save(); raise


def main():
    require(sys.dont_write_bytecode and not sys.flags.optimize, 'use Python -B without optimization')
    parser = argparse.ArgumentParser(); parser.add_argument('--inputs-sha', required=True); parser.add_argument('--helper-sha', required=True)
    Archive(parser.parse_args()).execute()


if __name__ == '__main__':
    main()

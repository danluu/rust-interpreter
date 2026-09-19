#!/usr/bin/env python3
"""Remove only the inventoried, completed Ruff profile targets after archival."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'oxc-runtime-compatibility'))
import acquire_runtime_source as a

OWNER = a.OWNER
PROFILE_OWNER = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
PRIOR = PROFILE_OWNER / '.work/ruff-hir-self-profile-02'
CONTINUED = PROFILE_OWNER / '.work/ruff-hir-self-profile-continuation-01'
ROOT = PRIOR / 'targets'
WORK = OWNER / '.work/ruff-profile-target-cleanup-01'
ASSESSMENT = OWNER / '.work/ruff-profile-target-cleanup-assessment-01.json'
FIELDS = ['dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns']


def identity(path):
    value = Path(path).lstat()
    return {name: getattr(value, 'st_' + name) for name in FIELDS}


def snapshot():
    a.ordinary(ROOT, directory=True)
    rows = {'.': identity(ROOT)}
    allocated = ROOT.lstat().st_blocks * 512
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        for name in sorted([*dirs, *files]):
            path = Path(directory) / name
            value = path.lstat()
            a.require(path.resolve(strict=True) == path and
                      (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)), 'indirect/special cache entry')
            rows[str(path.relative_to(ROOT))] = identity(path)
            allocated += value.st_blocks * 512
    return rows, allocated


class Cleanup:
    def __init__(self, plan, freeze, expected):
        a.require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize, 'fixed owner/Python required')
        self.plan_path, self.freeze_path, self.expected = plan, freeze, expected
        self.plan, self.frozen = a.read(plan), a.read(freeze)
        a.require(self.plan['root'] == str(ROOT) and self.plan['work'] == str(WORK), 'cleanup target differs')
        a.require(dict(os.environ) == self.plan['environment'], 'cleanup environment differs')
        self.owned = a.load('oxc_cleanup_owned', OWNER/'experiments/stable-cgu/owned_stage.py')
        self.guard()
        a.absent(WORK)
        WORK.mkdir()
        self.record = dict(status='waiting', root=str(ROOT), pid=os.getpid(), parent_pid=os.getppid(),
            started_at=time.time(), children=[], deleted=[], benchmark=False)
        self.save()

    def save(self):
        self.owned.write(WORK/'receipt.json', self.record)

    def guard(self):
        a.require(a.sha(self.freeze_path) == self.expected, 'cleanup freeze changed')
        for name, digest in self.frozen['files'].items():
            a.frozen_input_file(name, self.plan['executors'])
            a.require(a.sha(name) == digest, 'cleanup evidence/source changed: ' + name)
        for name, proof in self.plan['executors'].items():
            a.require(str(Path(name).resolve(strict=True)) == proof['resolved'] and a.stamp(name) == proof['stamp']
                      and a.sha(name) == proof['sha256'], 'cleanup executor changed')
        a.require(list(os.uname()) == self.plan['platform'], 'cleanup platform changed')

    def probe(self, label):
        spec = self.plan['commands'][len(self.record['children'])]
        a.require(spec['label'] == label, 'cleanup probe order changed')
        out = WORK/'commands'/label
        try:
            self.owned.run(spec['argv'], cwd=OWNER, env=self.plan['environment'], out=out,
                           capacity_root=OWNER, expected=tuple(spec['expected']))
        finally:
            if (out/'receipt.json').exists():
                self.record['children'].append(dict(label=label,path=str(out),receipt=a.read(out/'receipt.json')))
                self.save()
        a.require((out/'stderr').read_bytes() == b'' and (out/'stdout').stat().st_size < 1024**2,
                  'unexpected cleanup probe diagnostics')
        return a.read(out/'receipt.json'), (out/'stdout').read_text()

    def preservation(self):
        assessment = a.read(ASSESSMENT)
        a.require(assessment['root'] == str(ROOT) and not assessment['outside_hardlink_candidates'], 'unowned cache links')
        for name,digest in assessment['proofs'].items():
            a.require(a.sha(name) == digest, 'preserved qualification proof changed')
        prior = a.read(PRIOR/'supervision.json')
        continued = a.read(CONTINUED/'supervision.json')
        before = a.read(PRIOR/'result.json')
        result = a.read(CONTINUED/'result.json')
        a.require(prior['status'] == before['status'] == 'failed' and
                  prior['error'] == before['error'] == "RuntimeError('self-profile output exceeds bound')",
                  'original retained failure differs')
        a.require(continued['status'] == result['status'] == 'passed' and result['commands'] == 9 and
                  result['assertions_unchanged'] and result['cross_mode_bytecode_equal'] and
                  result['completed_compiles_rerun'] is False and
                  before['restored_source'] == result['restored_source'] ==
                  dict(files=11119,bytes=89102713,exact_membership=True), 'profile history incomplete')
        recipes = []
        for record, name, count, status in [(prior,'ruff-profile-02',5,1),
                                          (continued,'ruff-profile-continuation-01',9,0)]:
            outer_name = ('ruff-hir-self-profile-supervisor-02' if count == 5
                          else 'ruff-hir-self-profile-continuation-supervisor-01')
            outer = a.read(PROFILE_OWNER/'.work/experiments'/outer_name/'status.json')
            a.require(outer['status'] == 'finished' and outer['returncode'] == status and
                      record['pid'] == outer['child_pid'] and record['parent_pid'] == outer['supervisor_pid'] and
                      record['finished_at'] <= outer['finished_at'], 'profile owner has not completed')
            recipe = a.read(PROFILE_OWNER/'experiments/runtime-application-admission'/name/'plan/plan.json')
            recipes.append(recipe)
            a.require(len(record['children']) == count, 'profile child count differs')
            for observed, planned in zip(record['children'], recipe['commands']):
                child = observed['receipt']
                a.require(observed['label'] == planned['label'] and child['command'] == planned['command'] and
                          child['cwd'] == planned['cwd'] and
                          child['environment'] == planned.get('environment',recipe['child_environment']) and
                          child['status'] == 'finished' and child['returncode'] == planned['expected_returncode'] == 0 and
                          child['supervisor_pid'] == record['pid'] and
                          record['admitted_at'] <= child['started_at'] <= child['finished_at'] <= record['finished_at'],
                          'unfinished or foreign profile child')
                if observed['label'].endswith('-cargo'):
                    mode = observed['label'].split('-')[1]
                    a.require(mode in ['baseline','candidate'] and
                              child['environment']['CARGO_TARGET_DIR'] == str(ROOT/mode),
                              'target was not created by the completed recipe')
        a.require([x['label'] for x in prior['children']+continued['children']] ==
                  [x['label'] for x in recipes[0]['commands']], 'continued history differs from original recipe')
        result_root = PROFILE_OWNER/'results/runtime-ruff-hir-self-profile-01'
        manifest = a.read(result_root/'manifest.json')
        with tarfile.open(result_root/'evidence.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            a.require(len(members) == len(manifest) == 1894 and
                      {row.name for row in members} == set(manifest), 'archive membership changed')
            seen = {}
            for row in members:
                proof = manifest[row.name]
                a.require(proof['source'] == '/'+row.name, 'archive source mapping differs')
                if row.islnk():
                    a.require(row.linkname in seen and seen[row.linkname] == proof['sha256'] and row.size == 0,
                              'archive hardlink is not a prior identical member')
                else:
                    a.require(row.isfile() and row.size == proof['bytes'], 'archive member type/size changed')
                stream = archive.extractfile(row)
                digest = hashlib.sha256(); size = 0
                while block := stream.read(1024**2):
                    self.owned.disk(OWNER,9); digest.update(block); size += len(block)
                a.require(size == proof['bytes'] and digest.hexdigest() == proof['sha256'], 'archive member changed')
                seen[row.name] = digest.hexdigest()
            while archive.fileobj.read(1024**2): self.owned.disk(OWNER,9)
        # Every live profile, compiler record, artifact and raw receipt remains
        # outside the target root and must match the complete verified archive.
        preserved = {}; wrappers = 0
        for name, proof in manifest.items():
            path = Path(proof['source'])
            if path.is_relative_to(PRIOR) or path.is_relative_to(CONTINUED):
                a.require(not path.is_relative_to(ROOT) and path.resolve(strict=True) == path and
                          a.sha(path) == proof['sha256'], 'live retained profile evidence changed')
                preserved[str(path)] = proof['sha256']
                if path.name == 'invocation.json':
                    wrapper = a.read(path); wrappers += 1
                    a.require(wrapper['status'] == 'finished' and wrapper['returncode'] == 0 and
                              wrapper['finish_unix_ns']/1e9 <= continued['finished_at'],
                              'profile compiler wrapper unfinished')
        a.require(wrappers == 650, 'profile wrapper retention count differs')
        self.owned.write(WORK/'preserved-evidence.json',preserved)
        return assessment

    def remove(self, rows):
        expected = dict(rows)
        expected_parent = identity(ROOT.parent)
        links = {}
        for name, row in rows.items():
            if stat.S_ISREG(row['mode']): links.setdefault((row['dev'],row['ino']),[]).append(name)
        for names in links.values():
            a.require(rows[names[0]]['nlink'] == len(names), 'cache inode has an outside hardlink')
        def path(name): return ROOT if name == '.' else ROOT/name
        def parent(name): return str(Path(name).parent) if name != '.' else None
        def check(name):
            a.require(identity(path(name)) == expected[name] and path(name).resolve(strict=True) == path(name),
                      'cache entry identity changed: ' + name)
        def parent_before(name):
            key = parent(name)
            if key is None:
                a.require(identity(ROOT.parent) == expected_parent, 'outer owned directory changed')
            else: check(key)
            return key
        def finished(name, parent_key):
            del expected[name]
            if parent_key is not None:
                before = expected[parent_key]
                after = identity(path(parent_key))
                a.require(all(after[k] == before[k] for k in ['dev','ino','mode']), 'cache parent was replaced')
                expected[parent_key] = after
            self.record['deleted'].append(name)
            with (WORK/'deleted.jsonl').open('a') as ledger:
                ledger.write(json.dumps(dict(path=str(path(name)),time=time.time()))+'\n')
        # Keep each inode open while unlinking its complete admitted name set.
        # Only our prior unlink may alter nlink/ctime for remaining aliases.
        for names in sorted(links.values()):
            check(names[0])
            fd = os.open(path(names[0]), os.O_RDONLY|os.O_NOFOLLOW)
            try:
                for name in names:
                    self.owned.disk(OWNER,9)
                    check(name)
                    key = parent_before(name)
                    before = expected[name]
                    os.unlink(path(name))
                    after_stat = os.fstat(fd)
                    after = {k:getattr(after_stat,'st_'+k) for k in FIELDS}
                    a.require(all(after[k] == before[k] for k in ['dev','ino','mode','size','mtime_ns'])
                              and after['nlink'] == before['nlink']-1, 'unexpected inode change during owned unlink')
                    finished(name,key)
                    for remaining in names:
                        if remaining in expected:
                            a.require(identity(path(remaining)) == after, 'hardlink alias changed during owned unlink')
                            expected[remaining] = after
            finally: os.close(fd)
        for name in sorted(list(expected),key=lambda value:(len(Path(value).parts),value),reverse=True):
            self.owned.disk(OWNER,9)
            check(name)
            a.require(stat.S_ISDIR(expected[name]['mode']) and not os.listdir(path(name)), 'unexpected remaining cache member')
            key = parent_before(name)
            os.rmdir(path(name))
            finished(name,key)
        a.require(not expected and not ROOT.exists() and not ROOT.is_symlink(), 'cache removal incomplete')

    def execute(self):
        try:
            with self.owned.workload_lock(self.plan['canonical_lock'],600):
                self.record.update(status='running',admitted_at=time.time(),free_bytes_before=self.owned.disk(OWNER,9))
                self.save();self.guard()
                assessment = self.preservation()
                rows,allocated = snapshot()
                initial = {name:{key:row[key] for key in FIELDS} for name,row in assessment['entries'].items()}
                initial['.'] = assessment['root_stamp']
                a.require(rows == initial and len(rows) == 14139 and allocated <= assessment['allocated_bytes']+16*2**20,
                          'cache membership, identity or allocation bound changed')
                self.owned.write(WORK/'admitted-inventory.json',dict(entries=rows,allocated_bytes=allocated))
                receipt,stdout = self.probe('open-handles')
                a.require(receipt['returncode'] == 1 and stdout == '', 'cache has open handles')
                receipt,stdout = self.probe('owned-pids')
                for line in stdout.splitlines():
                    fields=line.split()
                    a.require(len(fields)>=9,'malformed process identity')
                    a.require(fields[3:8] != self.plan['owned_start_times'].get(fields[0]), 'an original owned process is still alive')
                self.guard()
                before_remove,_ = snapshot()
                a.require(before_remove == rows,'cache changed after read-only probes')
                self.remove(rows)
                self.preservation();self.guard()
                self.record.update(status='passed',deleted_entries=len(self.record['deleted']),cache_absent=True,
                    source_and_evidence_preserved=True,free_bytes_after=self.owned.disk(OWNER,9))
        except BaseException as error:
            self.record.update(status='failed',error=repr(error));raise
        finally:
            self.record['finished_at']=time.time();self.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--freeze',type=Path,required=True)
    parser.add_argument('--frozen-sha256',required=True)
    args=parser.parse_args()
    Cleanup(args.plan,args.freeze,args.frozen_sha256).execute()

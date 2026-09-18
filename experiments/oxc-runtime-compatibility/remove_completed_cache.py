#!/usr/bin/env python3
"""Remove only the inventoried, completed Oxc diagnostic cache after archival."""
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

import acquire_runtime_source as a

OWNER = a.OWNER
ROOT = OWNER / '.work/oxc-runtime-compatibility-01/cache'
WORK = OWNER / '.work/oxc-runtime-cache-cleanup-01'
ASSESSMENT = OWNER / '.work/oxc-runtime-cache-cleanup-assessment-01.json'
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
        previous = a.read(ROOT.parent/'receipt.json')
        outer = a.read(OWNER/'.work/experiments/oxc-runtime-compatibility-supervisor-01/status.json')
        a.require(previous['status'] == 'passed' and previous['source_restored'] and previous['runtime_compatibility']
                  and len(previous['children']) == len(previous['states']) == 16 and outer['status'] == 'finished'
                  and outer['returncode'] == 0 and previous['pid'] == outer['child_pid']
                  and previous['finished_at'] <= outer['finished_at'], 'cache owner has not completed')
        recipe = a.read(OWNER/'experiments/oxc-runtime-compatibility/runtime-plan-01/plan.json')
        a.require(len(recipe['commands']) == 16, 'original ownership recipe incomplete')
        for observed, planned in zip(previous['children'], recipe['commands']):
            child = observed['receipt']
            a.require(child['command'] == planned['argv'] and child['status'] == 'finished'
                      and child['returncode'] == planned['expected_returncode']
                      and child['finished_at'] <= previous['finished_at'], 'unfinished or foreign cache child')
            selected = child['command'][child['command'].index('--workspace-cache-root')+1]
            a.require(selected == str(ROOT/planned['engine']), 'cache was not created by the completed recipe')
        manifest = a.read(OWNER/'results/oxc-runtime-compatibility-01/manifest.json')['members']
        with tarfile.open(OWNER/'results/oxc-runtime-compatibility-01/evidence.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            a.require(len(members) == len(manifest) == 856 and {row.name for row in members} == set(manifest), 'archive membership changed')
            for row in members:
                a.require(row.isfile() and row.size == manifest[row.name]['bytes'] and
                          hashlib.sha256(archive.extractfile(row).read()).hexdigest() == manifest[row.name]['sha256'],
                          'archive member changed')
            while archive.fileobj.read(1024**2):
                self.owned.disk(OWNER,9)
        # The live retained artifacts, raw outputs, argv records and receipts
        # remain outside the deletion root and must match the verified archive.
        preserved = {}
        prefix = '.work/oxc-runtime-compatibility-01/'
        for name, proof in manifest.items():
            if name.startswith(prefix):
                path = OWNER/name
                a.require(not path.is_relative_to(ROOT) and a.sha(path) == proof['sha256'], 'live retained evidence changed')
                preserved[name] = proof['sha256']
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
                a.require(rows == initial and len(rows) == 5615 and allocated <= assessment['allocated_bytes']+16*2**20,
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

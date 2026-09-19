#!/usr/bin/env python3
"""Remove only the inventoried, completed Ruff profile targets after archival."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import shlex
import sys
import tarfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'oxc-runtime-compatibility'))
import acquire_runtime_source as a

OWNER = a.OWNER
from assess import A, R, RUN, ROOTS, ASSESSMENT, snapshot, identity
from preserve import DEST, RESULT, NATIVE, NATIVE_SHA

WORK = OWNER / '.work/ruff-diagnostic-target-cleanup-01'
HISTORY = A / '.work/ruff-hir-diagnostic-supervision-01'
OUTER = A / '.work/experiments/ruff-hir-diagnostic-supervisor-01'
RECIPE = A / 'experiments/runtime-application-admission/ruff-diagnostic-01/plan.json'
INDEPENDENT = A / '.work/ruff-hir-diagnostic-independent-verification-01.json'
CORRECTION = A / '.work/ruff-hir-diagnostic-attribution-correction-01.json'
SOURCE_INVENTORY = A / '.work/ruff-source-acquisition-02/acquired-inventory.json'
FIELDS = ['dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns']
TESTS = ['registry::tests::'+name for name in ['documentation','rule_naming_convention',
    'check_code_serialization','linter_parse_code','rule_size','linter_sorting']]

class Cleanup:
    def __init__(self, plan, freeze, expected):
        a.require(Path.cwd() == OWNER and sys.dont_write_bytecode and not sys.flags.optimize, 'fixed owner/Python required')
        self.plan_path, self.freeze_path, self.expected = plan, freeze, expected
        self.plan, self.frozen = a.read(plan), a.read(freeze)
        a.require(self.plan['roots'] == {key:str(root) for key,root in ROOTS.items()} and self.plan['work'] == str(WORK), 'cleanup target differs')
        a.require(dict(os.environ) == self.plan['environment'], 'cleanup environment differs')
        self.owned = a.load('oxc_cleanup_owned', OWNER/'experiments/stable-cgu/owned_stage.py')
        self.guard()
        a.absent(WORK)
        WORK.mkdir()
        self.record = dict(status='waiting', roots={key:str(root) for key,root in ROOTS.items()}, pid=os.getpid(), parent_pid=os.getppid(),
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


    def archive(self, directory, count, supplement=False):
        manifest = a.read(directory/'manifest.json')
        if supplement: manifest = manifest['members']
        with tarfile.open(directory/'evidence.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            a.require(len(members) == len(manifest) == count and
                      {row.name for row in members} == set(manifest), 'archive membership differs')
            seen = {}
            for row in members:
                proof = manifest[row.name]
                if not supplement: a.require(proof['source'] == '/'+row.name, 'archive source differs')
                if row.islnk():
                    a.require(not supplement and row.linkname in seen and
                              seen[row.linkname] == proof['sha256'] and row.size == 0, 'archive link differs')
                else: a.require(row.isfile() and row.size == proof['bytes'], 'archive member type/size differs')
                digest = hashlib.sha256(); size = 0
                stream = archive.extractfile(row)
                while block := stream.read(1024**2):
                    self.owned.disk(OWNER,9); digest.update(block); size += len(block)
                a.require(size == proof['bytes'] and digest.hexdigest() == proof['sha256'], 'archive bytes differ')
                seen[row.name] = digest.hexdigest()
            while archive.fileobj.read(1024**2): self.owned.disk(OWNER,9)
        return manifest

    def preservation(self, before):
        assessment = a.read(ASSESSMENT)
        a.require(set(assessment['roots']) == set(ROOTS), 'assessment roots differ')
        for mode,root in ROOTS.items():
            proof = assessment['roots'][mode]
            a.require(proof['root'] == str(root) and not proof['outside_hardlink_candidates'], 'unowned cache')
        terminal = a.read(HISTORY/'receipt.json')
        workflow = a.read(HISTORY/'workflow/receipt.json')
        outer = a.read(OUTER/'status.json')
        recipe = a.read(RECIPE)
        independent = a.read(INDEPENDENT)
        correction = a.read(CORRECTION)
        verification = a.read(HISTORY/'workflow-verification.json')
        a.require(terminal['status'] == independent['status'] == 'passed' and
                  terminal['restored_source_bytes_verified'] and independent['source_restored'] and
                  independent['exact_source_membership'] and independent['workflow_calls'] == 24 and
                  independent['receipt_sha256'] == a.sha(HISTORY/'receipt.json') and
                  terminal['verification_sha256'] == a.sha(HISTORY/'workflow-verification.json') and
                  verification['commands'] == 24 and verification['exact_artifact_hashes_verified'] == 16 and
                  verification['restored_original_build_and_execution_verified'] and
                  not correction['original_history_modified'] and not correction['original_raw_counts_modified'],
                  'completed diagnostic verification differs')
        a.require(outer['status'] == workflow['status'] == 'finished' and
                  outer['returncode'] == workflow['returncode'] == 0 and terminal['child'] == workflow and
                  terminal['pid'] == outer['child_pid'] == workflow['supervisor_pid'] and
                  terminal['parent_pid'] == outer['supervisor_pid'] and
                  terminal['started_at'] <= workflow['started_at'] <= workflow['finished_at'] <=
                  terminal['finished_at'] <= outer['finished_at'] and workflow['command'] == recipe['command'] and
                  workflow['cwd'] == str(R) and workflow['environment'] == recipe['environment'],
                  'unfinished or different original workflow')
        for stream in ['stdout','stderr']:
            a.require(a.sha(HISTORY/'workflow'/stream) == workflow[stream+'_sha256'], 'workflow raw changed')
        records = a.read(RUN/'records.json')
        a.require(len(records) == 24, 'diagnostic call count differs')
        final = {}
        for mode,root in ROOTS.items():
            selected = [row for row in records if row['mode'] == mode]
            a.require([row['state'] for row in selected] == [0,-1,1,2,3,4,5,-2], 'source history differs')
            for row in selected:
                a.require(len(row['calls']) == 1 and row['tests'] == TESTS, 'selected assertions differ')
                call = row['calls'][0]
                expected = (101 if mode == 'native' else 1) if row['state'] == -1 else 0
                a.require(call['returncode'] == expected, 'unfinished or unexpected original call')
                if mode == 'native':
                    argv = call['command']
                    a.require(argv.count('--target-dir') == 1 and argv[argv.index('--target-dir')+1] == str(root),
                              'native target not owned by original workflow')
                else:
                    launch = call['launch']
                    a.require(launch['workspace_path'] == str(root.parent) and
                              Path(launch['artifact_path']).is_relative_to(root), 'guest target differs')
            final[mode] = selected[-1]['calls'][0]
        running = [shlex.split(line.strip()[9:-1]) for line in final['native']['stderr'].splitlines()
                   if line.strip().startswith('Running `') and line.strip().endswith('`')]
        a.require([str(NATIVE),'--exact','--test-threads=1',*TESTS] in running, 'final native executable argv differs')
        original = self.archive(DEST/'original-archive',263)
        supplemental = self.archive(RESULT,13,True)
        retained = a.read(DEST/'receipt.json')
        a.require(len(retained['final_artifacts']) == 12 and len(retained['original_replay_fingerprints']) == 19 and
                  retained['assessment'] == dict(path=str(ASSESSMENT),sha256=a.sha(ASSESSMENT)), 'retention differs')
        a.require(supplemental['receipt.json']['sha256'] == a.sha(DEST/'receipt.json'), 'supplement receipt differs')
        for name,proof in retained['final_artifacts'].items():
            copy = Path(proof['retained']); source = Path(proof['source'])
            a.ordinary(copy)
            a.require(copy.stat().st_nlink == 1 and a.sha(copy) == proof['sha256'] and
                      copy.stat().st_size == proof['bytes'] and
                      supplemental['artifacts/'+name] == dict(bytes=proof['bytes'],sha256=proof['sha256']),
                      'retained final artifact changed')
            if before:
                a.require(identity(source) == proof['source_identity'] and a.sha(source) == proof['sha256'] and
                          source.stat().st_ino != copy.stat().st_ino, 'final source artifact changed')
        a.require(retained['final_artifacts']['native/'+NATIVE.name]['sha256'] == NATIVE_SHA, 'final native bytes differ')
        for mode in ['baseline','candidate']:
            mapping = retained['guest_output_directories'][mode]
            artifact = Path(final[mode]['launch']['artifact_path'])
            a.require(str(artifact.parent) == mapping['path'] and len(mapping['names']) == 5 and
                      retained['final_artifacts'][mode+'/'+artifact.name]['sha256'] == final[mode]['launch']['artifact_sha256'],
                      'final guest artifact mapping differs')
            if before: a.require(sorted(p.name for p in artifact.parent.iterdir()) == mapping['names'], 'guest output set changed')
            workspace = retained['workspaces'][mode]; parent = ROOTS[mode].parent
            wanted = workspace['initial_names'] if before else [n for n in workspace['initial_names'] if n != 'target']
            a.require(sorted(p.name for p in parent.iterdir()) == wanted, 'workspace membership changed')
            for name,proof in workspace['files'].items():
                a.require(identity(parent/name) == proof['identity'] and a.sha(parent/name) == proof['sha256'],
                          'workspace identity bytes changed')
        for name,proof in retained['original_replay_fingerprints'].items():
            a.require(original[name.lstrip('/')] == proof, 'replay archive mapping changed')
            if before: a.require(a.sha(name) == proof['sha256'], 'original replay bytes changed')
        for name,proof in retained['live_evidence'].items():
            a.require(original[name.lstrip('/')] == proof and a.sha(name) == proof['sha256'], 'live evidence changed')
        for path in [INDEPENDENT,CORRECTION]:
            a.require(original[str(path).lstrip('/')]['sha256'] == a.sha(path), 'original interpretation proof changed')
        # Full current source membership and bytes, excluding its recorded Git/ownership metadata.
        inventory = a.read(SOURCE_INVENTORY); source = R/'.work/sources/ruff'; names = set()
        for directory,dirs,files in os.walk(source,followlinks=False):
            if Path(directory) == source: dirs[:] = [name for name in dirs if name != '.git']
            for name in files:
                path = Path(directory)/name; relative = str(path.relative_to(source))
                if relative == '.rust-interp-owned.json': continue
                names.add(relative); proof = inventory[relative]; stamp = identity(path)
                if proof['kind'] == 'symlink':
                    a.require(stat.S_ISLNK(stamp['mode']) and os.readlink(path) == proof['target'], 'source link differs')
                else:
                    a.require(stat.S_ISREG(stamp['mode']) and path.resolve(strict=True) == path and
                              stamp['size'] == proof['bytes'] and a.sha(path) == proof['sha256'], 'source bytes differ')
                a.require(identity(path) == stamp, 'source changed while read')
        a.require(names == set(inventory) and len(names) == 11119, 'source membership differs')
        return assessment
    def remove(self, ROOT, rows):
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
            self.record['deleted'].append(str(path(name)))
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
                self.save(); self.guard()
                assessment = self.preservation(True); admitted = {}
                for mode,root in ROOTS.items():
                    rows,allocated = snapshot(root); proof = assessment['roots'][mode]
                    a.require(rows == proof['entries'] and allocated <= proof['allocated_bytes']+16*2**20,
                              'cache membership, identity or allocation differs')
                    admitted[mode] = dict(entries=rows,allocated_bytes=allocated)
                    receipt,stdout = self.probe('open-handles-'+mode)
                    a.require(receipt['returncode'] == 1 and stdout == '', 'cache has open handles')
                self.owned.write(WORK/'admitted-inventory.json',admitted)
                receipt,stdout = self.probe('owned-pids')
                for line in stdout.splitlines():
                    fields = line.split()
                    a.require(len(fields)>=9,'malformed process identity')
                    a.require(fields[3:8] != self.plan['owned_start_times'].get(fields[0]), 'original process still alive')
                self.guard()
                for mode,root in ROOTS.items():
                    rows,_ = snapshot(root)
                    a.require(rows == admitted[mode]['entries'], 'cache changed after probes')
                    self.remove(root,rows)
                self.preservation(False); self.guard()
                a.require(len(self.record['children']) == 4 and len(self.record['deleted']) == 22953,
                          'removal/probe count differs')
                self.record.update(status='passed',deleted_entries=len(self.record['deleted']),all_three_targets_absent=True,
                    source_and_evidence_preserved=True,free_bytes_after=self.owned.disk(OWNER,9))
        except BaseException as error:
            self.record.update(status='failed',error=repr(error)); raise
        finally:
            self.record['finished_at']=time.time(); self.save()
if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--freeze',type=Path,required=True)
    parser.add_argument('--frozen-sha256',required=True)
    args=parser.parse_args()
    Cleanup(args.plan,args.freeze,args.frozen_sha256).execute()

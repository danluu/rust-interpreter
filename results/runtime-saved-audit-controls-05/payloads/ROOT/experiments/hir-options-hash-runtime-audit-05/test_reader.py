"""Tiny saved-evidence callback fixtures; no real runtime/provider paths opened.

Only reader.py is imported. Fake /fixture records exercise the reader's mapping,
process association and snapshot-accounting contracts. Snapshot verification is
an explicit metadata callback; real gzip EOF remains the qualified v2 helper's
responsibility and is mandatory in the actual saved-evidence orchestrator.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import types
import unittest


def load_reader():
    path = Path(__file__).with_name('reader.py')
    spec = importlib.util.spec_from_file_location('runtime04_saved_reader_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.R = Path('/fixture/owner')
    module.SOURCE = Path('/fixture/runtime-source')
    return module


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stamp(size=1, inode=101, mode=stat.S_IFREG | 0o600):
    return dict(dev=1, ino=inode, mode=mode, nlink=1, size=size, mtime_ns=2, ctime_ns=3)


class Saved:
    def __init__(self):
        self.data = {}
        self.stamps = {}

    def bytes(self, path, data):
        path = str(path)
        self.data[path] = data
        self.stamps[path] = stamp(len(data), len(self.stamps)+101)
        return digest(data)

    def json(self, path, value):
        return self.bytes(path, encoded(value))

    def read(self, path):
        return json.loads(self.data[str(path)])

    def raw(self, path):
        return self.data[str(path)]

    def sha(self, path):
        return digest(self.raw(path))

    def identity(self, path):
        return copy.deepcopy(self.stamps[str(path)])


class OwnerFixture:
    def __init__(self, phase='preflight'):
        self.reader = load_reader(); self.saved = Saved(); s = self.saved
        self.phase = phase; self.paths = self.reader.phase_paths(phase)
        packet, work, outer = [self.paths[k] for k in ['packet', 'work', 'outer']]
        environment = {'PATH':'/fixture/bin', 'HOME':'/fixture/home'}
        command = ['/fixture/python','-B','/fixture/supervisor','--run-id','fixture','--',
                   '/fixture/python','-B','/fixture/runtime-entry']
        self.plan = dict(phase=phase, owner=str(self.reader.R), work=str(work),
            supervisor_work=str(outer), launch_environment=environment, environment=environment,
            capacity=dict(entry_gib=24,stop_gib=9,floor_gib=8,combined_namespace_bytes=14*2**30,evidence_bytes=256*2**20))
        self.launch = dict(cwd=str(self.reader.R), command=command, environment=environment,
            capacity=self.plan['capacity'], inputs_sha256=s.bytes(packet/'inputs.json',b'wire'),
            plan_sha256=s.json(packet/'plan.json',self.plan),
            snapshot_plan_sha256=s.bytes(packet/'snapshot-plan.json',b'projection'))
        self.terminal = dict(status='passed', phase=phase, pid=103, parent_pid=102,
            application_qualified=False,performance_measurement=False,exporter_qualified=False,std_mir_prepared=False,
            inputs_sha256=self.launch['inputs_sha256'],plan_sha256=self.launch['plan_sha256'],
            snapshot_plan_sha256=self.launch['snapshot_plan_sha256'],started_at=12,admitted_at=13,finished_at=20,
            free_bytes_before=24*2**30,free_bytes_after=9*2**30)
        self.outer = dict(status='finished',returncode=0,child_pid=103,supervisor_pid=102,
            command=command[6:],cwd=str(self.reader.R),child_started_at=11,finished_at=21,
            plan_sha256=s.bytes(outer/'plan.json',b'outer-plan'),log_sha256=s.bytes(outer/'command.log',b'outer-log'))
        launcher_path = Path('/fixture/launcher/record.json')
        launcher_source = Path('/fixture/launcher-source.py')
        self.expected = dict(launch=s.json(packet/'launch.json',self.launch),inputs=self.launch['inputs_sha256'],
            snapshot_plan=self.launch['snapshot_plan_sha256'],receipt=s.json(work/'receipt.json',self.terminal),
            launcher_record=str(launcher_path))
        self.launcher = dict(status='terminal-observed',returncode=0,launcher_returncode=0,
            outer_sha256=s.json(outer/'status.json',self.outer),command=command,cwd=str(self.reader.R),
            environment=environment,launch_sha256=self.expected['launch'],started_at=9,launcher_finished_at=10,
            terminal_observed_at=22,finished_at=22,supervisor_pid=102,controller_pid=103,
            launcher_source_path=str(launcher_source),launcher_source_sha256=s.bytes(launcher_source,b'fixture source'),
            stdout_sha256=s.json(launcher_path.parent/'stdout',dict(directory=str(outer),supervisor_pid=102)),
            stderr_sha256=s.bytes(launcher_path.parent/'stderr',b''))
        self.expected['launcher_record_sha256'] = s.json(launcher_path,self.launcher)

    def check(self):
        return self.reader.owner(self.plan,self.launch,self.terminal,self.outer,self.launcher,
            phase=self.phase,expected=self.expected,sha=self.saved.sha,read_json=self.saved.read)


class Owner(unittest.TestCase):
    def test_both_actual_phase_shapes_and_terminal_observation(self):
        for phase in ['preflight','installation']:
            f=OwnerFixture(phase);self.assertEqual(f.check(),f.paths)

    def test_failed_or_incomplete_owner_is_rejected(self):
        for status in ['failed','running','passed-awaiting-independent-audit']:
            f=OwnerFixture();f.terminal['status']=status
            with self.assertRaises(RuntimeError):f.check()

    def test_packet_and_source_digests_are_not_interchangeable(self):
        for key in ['launch','inputs','snapshot_plan','receipt','launcher_record_sha256']:
            f=OwnerFixture();f.expected[key]='f'*64
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()
        f=OwnerFixture();f.saved.bytes(f.launcher['launcher_source_path'],b'changed source')
        with self.assertRaises(RuntimeError):f.check()

    def test_supervisor_identity_command_and_context_are_bound(self):
        for key,value in [('child_pid',999),('supervisor_pid',999),('command',['foreign']),('cwd','/fixture/foreign')]:
            f=OwnerFixture();f.outer[key]=value
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()

    def test_wrapper_only_completion_does_not_claim_terminal(self):
        f=OwnerFixture();f.launcher['status']='finished'
        with self.assertRaises(RuntimeError):f.check()
        f=OwnerFixture();f.launcher['terminal_observed_at']=20
        with self.assertRaises(RuntimeError):f.check()
        f=OwnerFixture();f.launcher['finished_at']=21
        with self.assertRaises(RuntimeError):f.check()

    def test_actual_handoff_and_raw_are_required(self):
        f=OwnerFixture();f.saved.json('/fixture/launcher/stdout',dict(directory='/fixture/foreign',supervisor_pid=102))
        f.launcher['stdout_sha256']=f.saved.sha('/fixture/launcher/stdout')
        with self.assertRaises(RuntimeError):f.check()
        f=OwnerFixture();f.saved.bytes('/fixture/launcher/stderr',b'changed')
        with self.assertRaises(RuntimeError):f.check()

    def test_no_environment_or_capacity_relabeling(self):
        f=OwnerFixture();f.launcher['environment']={'PATH':'/fixture/other'}
        with self.assertRaises(RuntimeError):f.check()
        for key in ['free_bytes_before','free_bytes_after']:
            f=OwnerFixture();f.terminal[key]-=1
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()
        f=OwnerFixture();f.terminal['application_qualified']=True
        with self.assertRaises(RuntimeError):f.check()


class ChildFixture:
    def __init__(self):
        self.reader=load_reader();self.saved=Saved();self.desired=[];self.rows=[]
        self.terminal=dict(pid=100,parent_pid=99,admitted_at=10,finished_at=30,children=[])
        for index,(code,start,finish,psstart) in enumerate([(0,11,12,'Sat Sep 19 01:00:00 2026'),
                                                          (1,20,21,'Sat Sep 19 01:00:09 2026')]):
            output=Path('/fixture/work')/str(index);argv=['/fixture/rustc',str(index)]
            declaration=dict(argv=argv,cwd='/fixture/work',environment={'PATH':'/fixture/bin'},expected=[code],output=str(output))
            row=dict(status='finished',pid=200+index,supervisor_pid=100,parent_pid=99,command=argv,
                cwd=declaration['cwd'],environment=declaration['environment'],expected=[code],returncode=code,
                started_at=start,finished_at=finish,identity=dict(ps_returncode=0,
                    ps=f'{200+index} 100 {200+index} {psstart} ?? '+ ' '.join(argv),
                    cwd_returncode=0,cwd=f'p{200+index}\nfcwd\nn/fixture/work\n'),
                stdout_sha256=self.saved.bytes(output/'stdout',b'ok' if code==0 else b''),
                stderr_sha256=self.saved.bytes(output/'stderr',b'' if code==0 else b'fixture diagnostic'))
            self.desired.append(declaration);self.rows.append(row)
        self.plan=dict(children=copy.deepcopy(self.desired));self.sync()

    def sync(self):
        self.terminal['children']=[]
        for wanted,row in zip(self.desired,self.rows):
            path=Path(wanted['output'])/'receipt.json'
            self.terminal['children'].append(dict(path=str(path),sha256=self.saved.json(path,row),
                pid=row['pid'],returncode=row['returncode']))

    def check(self):
        return self.reader.child_history(self.plan,self.terminal,desired=self.desired,
            read_json=self.saved.read,read_bytes=self.saved.raw,sha=self.saved.sha)


class Children(unittest.TestCase):
    def test_complete_success_and_expected_diagnostic_failure(self):
        f=ChildFixture();r=f.check();self.assertEqual(len(r['children']),2)
        self.assertEqual([v['receipt']['returncode'] for v in r['children']],[0,1])

    def test_actual_nonoverlapping_pid_reuse_is_preserved(self):
        f=ChildFixture();r=f.rows[1];r['pid']=200;r['identity']['ps']=r['identity']['ps'].replace('201 100 201','200 100 200')
        r['identity']['cwd']=r['identity']['cwd'].replace('p201','p200');f.sync()
        answer=f.check();self.assertEqual([x['pid'] for x in answer['identities']],[200,200])

    def test_reused_pid_requires_distinct_observed_start_and_no_overlap(self):
        f=ChildFixture();r=f.rows[1];r['pid']=200;r['identity']['ps']=f.rows[0]['identity']['ps'].replace('/fixture/rustc 0','/fixture/rustc 1')
        r['identity']['cwd']=f.rows[0]['identity']['cwd'];f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=ChildFixture();f.rows[1]['started_at']=11;f.sync()
        with self.assertRaises(RuntimeError):f.check()

    def test_missing_fast_cwd_is_honestly_reported(self):
        f=ChildFixture();f.rows[1]['identity'].update(cwd_returncode=1,cwd='');f.sync()
        missing=f.check()['unavailable_contemporaneous_cwd'];self.assertEqual(len(missing),1)
        self.assertEqual(missing[0]['requested_cwd'],'/fixture/work')

    def test_fabricated_or_unexplained_cwd_is_rejected(self):
        for code,text in [(1,'n/fixture/work\n'),(2,''),(0,'')]:
            f=ChildFixture();f.rows[1]['identity'].update(cwd_returncode=code,cwd=text);f.sync()
            with self.subTest(code=code,text=text),self.assertRaises(RuntimeError):f.check()

    def test_process_parent_group_argv_and_raw_must_agree(self):
        for mutate in [lambda r:r.update(parent_pid=88),lambda r:r.update(command=['foreign']),
                       lambda r:r['identity'].update(ps=r['identity']['ps'].replace('200 100 200','200 100 999')),
                       lambda r:r.update(environment={'PATH':'foreign'})]:
            f=ChildFixture();mutate(f.rows[0]);f.sync()
            with self.assertRaises(RuntimeError):f.check()
        f=ChildFixture();f.saved.bytes('/fixture/work/0/stdout',b'changed')
        with self.assertRaises(RuntimeError):f.check()

    def test_exact_complete_reference_order_and_typed_returncode(self):
        f=ChildFixture();f.terminal['children'].reverse()
        with self.assertRaises(RuntimeError):f.check()
        f=ChildFixture();f.terminal['children'].pop()
        with self.assertRaises(RuntimeError):f.check()
        f=ChildFixture();f.rows[1]['returncode']=True;f.sync()
        with self.assertRaises(RuntimeError):f.check()


class ControlFixture:
    def __init__(self):
        self.reader=load_reader();self.saved=Saved();s=self.saved
        self.source=Path('/fixture/controls');self.work=Path('/fixture/control-work');self.audit=Path('/fixture/audit.json')
        module=Path('/fixture/module.py');tests=Path('/fixture/test_module.py')
        s.bytes(module,b'fixture selected source\n');s.bytes(tests,b'class Case:\n    def test_small(self):\n        pass\n    def test_other(self):\n        pass\n')
        names=['test_module.Case.test_other','test_module.Case.test_small'];argv=['/fixture/python','-m','fixture'];environment={'PATH':'/fixture/bin'}
        self.freeze=dict(files={str(p):dict(sha256=s.sha(p),stamp=[s.identity(p)[k] for k in
            ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]) for p in [module,tests]},routes={},
            expected_names=names,command=argv,environment=environment)
        self.result=dict(status='passed',expected_names=names,tests_run=2,failures=0,errors=0,skipped=0,
            expected_failures=0,unexpected_successes=0,child_processes=0,compiler_calls=0)
        childpath=self.work/'command/receipt.json'
        self.child=dict(status='finished',returncode=0,pid=303,supervisor_pid=302,parent_pid=301,command=argv,
            environment=environment,stdout_sha256=s.bytes(childpath.parent/'stdout',b''),
            stderr_sha256=s.bytes(childpath.parent/'stderr',b'test_other (test_module.Case.test_other) ... ok\ntest_small (test_module.Case.test_small) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n'))
        self.terminal=dict(status='passed',controls_passed=2,pid=302,parent_pid=301)
        self.report=dict(status='verified',controls=2,exact_names=names,raw_sha256={k:self.child[k+'_sha256'] for k in ['stdout','stderr']})
        self.modules=[module];self.tests=[tests];self.sync()

    def sync(self):
        s=self.saved;s.json(self.source/'inputs.json',self.freeze);s.json(self.work/'result.json',self.result)
        cp=self.work/'command/receipt.json'
        self.terminal.update(inputs_sha256=s.sha(self.source/'inputs.json'),result_sha256=s.sha(self.work/'result.json'),
            commands=[dict(path=str(cp),pid=self.child['pid'],sha256=s.json(cp,self.child))])
        self.report.update(receipt_sha256=s.json(self.work/'receipt.json',self.terminal),result_sha256=s.sha(self.work/'result.json'))
        s.json(self.audit,self.report)

    def check(self):
        return self.reader.controls(source=self.source,work=self.work,audit_path=self.audit,
            source_paths=self.modules,test_paths=self.tests,read_json=self.saved.read,read_bytes=self.saved.raw,
            sha=self.saved.sha,identity=self.saved.identity)


class Controls(unittest.TestCase):
    def test_closed_source_raw_names_and_audit_associate(self):
        f=ControlFixture();self.assertEqual(f.check()['controls'],2)

    def test_changed_frozen_source_or_unselected_module_rejects(self):
        f=ControlFixture();f.saved.bytes(f.modules[0],b'changed')
        with self.assertRaises(RuntimeError):f.check()
        f=ControlFixture();f.modules.append(Path('/fixture/unselected.py'))
        with self.assertRaises(RuntimeError):f.check()

    def test_control_counts_and_failures_are_typed(self):
        f=ControlFixture();f.result['tests_run']=True;f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=ControlFixture();f.result['skipped']=1;f.sync()
        with self.assertRaises(RuntimeError):f.check()

    def test_child_and_raw_history_cannot_be_rebound(self):
        f=ControlFixture();f.child['supervisor_pid']=999;f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=ControlFixture();f.saved.bytes(f.work/'command/stderr',b'forged raw')
        with self.assertRaises(RuntimeError):f.check()

    def test_test_names_and_footer_must_be_actual(self):
        f=ControlFixture();p=f.work/'command/stderr';raw=f.saved.raw(p).replace(b'OK\n',b'FAILED\n')
        f.child['stderr_sha256']=f.saved.bytes(p,raw);f.report['raw_sha256']['stderr']=f.child['stderr_sha256'];f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=ControlFixture();f.result['expected_names']=['other'];f.sync()
        with self.assertRaises(RuntimeError):f.check()



class SnapshotFixture:
    def __init__(self):
        self.reader=load_reader();self.saved=Saved();s=self.saved
        self.packet=Path('/fixture/runtime-packet');self.work=Path('/fixture/runtime-work')
        self.root=self.work/'source-snapshots';self.prior=Path('/fixture/prior/source-snapshots')
        aliases=[Path('/fixture/a.py'),Path('/fixture/alias.py')]
        for path in aliases:s.bytes(path,b'aliased fixture')
        own=self.packet/'inputs.json';s.bytes(own,b'compact fixture')
        rows=[dict(path=str(p),sha256=s.sha(p),size=len(s.raw(p)),identity=s.identity(p)) for p in [*aliases,own]]
        self.freeze=dict(snapshot_inputs=list(map(str,aliases)),files={r['path']:{k:v for k,v in r.items() if k!='path'} for r in rows[:-1]})
        key,ownkey=s.sha(aliases[0]),s.sha(own)
        compressed=b'fake compressed row'  # Metadata fixture only; never a gzip EOF claim.
        def blob(k,size):
            return dict(filename=k+'.gz',logical_sha256=k,logical_bytes=size,
                compressed_bytes=len(compressed),sha256=digest(compressed))
        blobs={key:blob(key,len(s.raw(aliases[0]))),ownkey:blob(ownkey,len(s.raw(own)))}
        reference=dict(path=str(self.prior/(key+'.gz')),identity=stamp(19,401),blob=blobs[key],evidence_root=str(self.prior))
        roots={str(self.prior):stamp(64,402,stat.S_IFDIR|0o700)}
        self.selection=dict(records=[reference],evidence_roots=roots)
        self.lineage={'fixture_lineage':'completed'};self.plan=dict(snapshot_reuse=copy.deepcopy(self.lineage))
        reuse={key:reference}
        self.projection=dict(policy='bounded-gzip-proof-snapshots-v2',limits=copy.deepcopy(self.reader.LIMITS),
            files={r['path']:r for r in rows},blobs=blobs,reuse=reuse,evidence_roots=roots,
            logical_bytes=sum(r['size'] for r in rows),unique_logical_bytes=sum(b['logical_bytes'] for b in blobs.values()),
            storage={key:dict(kind='reused',path=reference['path']),ownkey:dict(kind='stored')},
            compressed_bytes=38,new_compressed_bytes=19,reused_compressed_bytes=19,
            compressed_allocated_bytes=8192,new_compressed_allocated_bytes=4096,
            manifest_reservation_bytes=8*2**20)
        reservation=4096+4096+8*2**20+32*2**20
        self.snapshot=dict(limits=copy.deepcopy(self.reader.LIMITS),inputs_sha256=s.sha(own),
            remaining_evidence_reservation_bytes=32*2**20,evidence_cap_bytes=256*2**20,
            reuse_selection=copy.deepcopy(self.selection),projection=self.projection,
            projected_reservation_bytes=reservation,measured_existing_evidence_bytes=1000)
        physical={key:dict(kind='reused',path=reference['path']),ownkey:dict(kind='stored',path=str(self.root/(ownkey+'.gz')))}
        self.manifest=dict(policy=self.projection['policy'],projection_sha256=self.reader.digest(self.projection),
            full_logical_readback=True,full_gzip_eof=True,blobs=copy.deepcopy(blobs),reuse=copy.deepcopy(reuse),
            evidence_roots=copy.deepcopy(roots),storage=physical,
            files={r['path']:dict(path=physical[r['sha256']]['path'],sha256=r['sha256'],size=r['size'],encoding='gzip') for r in rows},
            compressed_bytes=38,new_compressed_bytes=19,reused_compressed_bytes=19)
        self.terminal=dict(snapshot_admission=dict(existing_evidence_bytes=1000,reserved_bytes=reservation))
        self.directory=dict(identity=stamp(64,403,stat.S_IFDIR|0o700),children=[ownkey+'.gz'])
        s.bytes(self.prior/(key+'.gz'),compressed);s.stamps[reference['path']]=copy.deepcopy(reference['identity'])
        s.bytes(self.root/(ownkey+'.gz'),compressed)
        self.expected_physical={reference['path']:copy.deepcopy(reference),
            str(self.root/(ownkey+'.gz')):dict(path=str(self.root/(ownkey+'.gz')),
                identity=s.identity(self.root/(ownkey+'.gz')),blob=copy.deepcopy(blobs[ownkey]),evidence_root=str(self.root))}
        self.verified=[];self.guard_calls=0;self.directory_calls=0;self.fail_reference=False;self.change_directory=False
        self.catalog=types.SimpleNamespace(select=self.select)
        self.snapshots=types.SimpleNamespace(verify_reference=self.verify_reference)
        self.expected_records=copy.deepcopy(rows);self.sync()

    def sync(self):
        self.manifest['projection_sha256']=self.reader.digest(self.projection)
        data=encoded(self.snapshot)
        self.terminal['snapshot_plan_sha256']=self.saved.bytes(self.packet/'snapshot-plan.json',data)
        self.saved.bytes(self.work/'snapshot-plan.json',data)
        self.terminal['source_snapshots_sha256']=self.saved.json(self.work/'source-snapshots.json',self.manifest)

    def select(self,rows,lineage):
        if rows!=self.expected_records or lineage!=self.lineage:raise RuntimeError('fixture selection association differs')
        return copy.deepcopy(self.selection)

    def verify_reference(self,reference,roots,guard):
        guard()
        if self.fail_reference:raise RuntimeError('fixture full-reference rejection')
        if reference['evidence_root'] not in roots:raise RuntimeError('fixture reference root omitted')
        if (set(reference)!={'path','identity','blob','evidence_root'}
                or set(reference['blob'])!={'filename','logical_sha256','logical_bytes','sha256','compressed_bytes'}
                or reference['path'] not in self.expected_physical
                or encoded(reference)!=encoded(self.expected_physical[reference['path']])):
            raise RuntimeError('fixture exact physical descriptor differs')
        b=reference['blob'];p=reference['path']
        if (b['sha256']!=self.saved.sha(p) or b['compressed_bytes']!=len(self.saved.raw(p))
                or encoded(reference['identity'])!=encoded(self.saved.identity(p))
                or Path(p).parent!=Path(reference['evidence_root'])
                or Path(p).name!=b['filename'] or b['filename']!=b['logical_sha256']+'.gz'):
            raise RuntimeError('fixture compressed bytes or identity differs')
        self.verified.append(copy.deepcopy(reference))

    def guard(self):self.guard_calls+=1

    def directory_record(self,path):
        if path!=self.root:raise RuntimeError('unexpected fixture directory')
        self.directory_calls+=1;value=copy.deepcopy(self.directory)
        if self.change_directory and self.directory_calls>1:value['identity']['mtime_ns']+=1
        return value

    def check(self):
        return self.reader.snapshot_readback(plan=self.plan,freeze=self.freeze,packet=self.packet,work=self.work,
            terminal=self.terminal,snapshot=self.snapshot,manifest=self.manifest,lineage=self.lineage,
            catalog=self.catalog,snapshots=self.snapshots,read_json=self.saved.read,sha=self.saved.sha,
            identity=self.saved.identity,directory_record=self.directory_record,guard=self.guard)


class Snapshots(unittest.TestCase):
    def test_complete_aliases_stored_and_reused_are_read_back(self):
        f=SnapshotFixture();r=f.check()
        self.assertEqual((r['logical_files'],r['physical_blobs'],r['new_physical_blobs'],r['reused_physical_blobs']),(3,2,1,1))
        self.assertEqual(len(f.verified),2);self.assertGreater(f.guard_calls,0)
        self.assertEqual(len(r['referenced_physical_paths']),2)

    def test_reference_verifier_failure_is_not_hidden(self):
        f=SnapshotFixture();f.fail_reference=True
        with self.assertRaisesRegex(RuntimeError,'full-reference rejection'):f.check()
        f=SnapshotFixture();row=copy.deepcopy(next(iter(f.expected_physical.values())))
        row['blob']['compressed_sha256']=row['blob'].pop('sha256')
        with self.assertRaisesRegex(RuntimeError,'exact physical descriptor'):
            f.verify_reference(row,f.selection['evidence_roots'],f.guard)

    def test_missing_logical_alias_or_physical_blob_rejects(self):
        f=SnapshotFixture();f.manifest['files'].pop('/fixture/alias.py');f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.manifest['blobs'].pop(next(iter(f.manifest['blobs'])));f.sync()
        with self.assertRaises(RuntimeError):f.check()

    def test_reused_path_and_alias_mapping_cannot_be_rebound(self):
        f=SnapshotFixture();key=next(iter(f.projection['reuse']));f.projection['storage'][key]['path']='/fixture/foreign.gz';f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.manifest['files']['/fixture/alias.py']['path']='/fixture/foreign.gz';f.sync()
        with self.assertRaises(RuntimeError):f.check()

    def test_current_logical_identity_must_still_match(self):
        f=SnapshotFixture();f.saved.stamps['/fixture/a.py']['ctime_ns']+=1
        with self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.saved.bytes('/fixture/a.py',b'changed bytes')
        with self.assertRaises(RuntimeError):f.check()

    def test_full_directory_membership_and_stability_are_required(self):
        f=SnapshotFixture();f.directory['children'].append('unexpected.gz')
        with self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.change_directory=True
        with self.assertRaises(RuntimeError):f.check()

    def test_total_and_new_accounting_and_reserve_are_distinct(self):
        for key in ['compressed_bytes','new_compressed_bytes','reused_compressed_bytes','compressed_allocated_bytes','new_compressed_allocated_bytes']:
            f=SnapshotFixture();f.projection[key]+=1;f.sync()
            with self.subTest(key=key),self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.snapshot['projected_reservation_bytes']-=4096;f.sync()
        with self.assertRaises(RuntimeError):f.check()
        f=SnapshotFixture();f.terminal['snapshot_admission']['existing_evidence_bytes']=256*2**20
        with self.assertRaises(RuntimeError):f.check()


if __name__=='__main__':
    unittest.main()

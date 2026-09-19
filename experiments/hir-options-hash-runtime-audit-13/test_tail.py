"""Focused actual integration functions with owned temporary files only.

These fixtures do not qualify a runtime, substitute saved receipts, or change
the original53 controls. No provider, compiler, or subprocess is invoked.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import audit

_spec = importlib.util.spec_from_file_location('tail_test_qualified_access',
    audit.QUALIFIED_AUDIT/'audit_io.py')
access = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(access)


class TailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='saved-audit-tail-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.outer = self.root/'supervisor'; self.outer.mkdir()
        self.preparation = self.root/'preparation'; self.preparation.mkdir()
        self.source = self.root/'supervise.py'; self.source.write_bytes(b'owned writer fixture\n')
        self.command = ['owned-python','-B','owned-controller.py']
        self.launch = dict(command=['owned-python','-B',str(self.source),'--run-id',self.outer.name,'--',*self.command])
        self.plan = dict(owner=str(self.root), command=self.command,
            supervisor_sha256=self.sha(self.source))
        (self.outer/'plan.json').write_bytes(audit.encoded(self.plan))
        (self.outer/'command.log').write_bytes(b'owned child output\n')
        # Nonempty supervisor bytes must be retained, not silently dropped.
        (self.outer/'supervisor.log').write_bytes(b'owned supervisor output\n')
        self.supervisor = dict(cwd=str(self.root),command=self.command,
            plan_sha256=self.sha(self.outer/'plan.json'),
            log_sha256=self.sha(self.outer/'command.log'))
        (self.outer/'status.json').write_bytes(audit.encoded(self.supervisor))

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def row(self, path):
        return dict(size=path.stat().st_size,sha256=self.sha(path),identity=access.stamp(path.stat()))

    def supervisor_proof(self):
        io = access.Access({str(self.source):self.row(self.source)},output_roots=[self.outer])
        return audit.supervisor_output_readback(io,self.outer,self.launch,self.supervisor,source=self.source)

    def test_supervisor_four_outputs_and_both_distinct_raw_streams(self):
        proof = self.supervisor_proof()
        self.assertEqual(proof['membership']['files'],4)
        self.assertEqual(proof['supervisor_stream']['sha256'],self.sha(self.outer/'supervisor.log'))
        self.assertEqual(proof['supervisor_stream']['identity'],access.stamp((self.outer/'supervisor.log').stat()))
        self.assertEqual(proof['command_stream']['sha256'],self.supervisor['log_sha256'])
        self.assertNotEqual(proof['command_stream']['sha256'],proof['supervisor_stream']['sha256'])

    def test_missing_supervisor_stream_rejected(self):
        (self.outer/'supervisor.log').unlink()
        with self.assertRaisesRegex(RuntimeError,'closed output membership'):
            self.supervisor_proof()

    def test_unexpected_supervisor_output_rejected(self):
        (self.outer/'unexpected').write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError,'closed output membership'):
            self.supervisor_proof()

    def test_supervisor_writer_rebinding_rejected(self):
        self.plan['supervisor_sha256']='0'*64
        (self.outer/'plan.json').write_bytes(audit.encoded(self.plan))
        self.supervisor['plan_sha256']=self.sha(self.outer/'plan.json')
        with self.assertRaisesRegex(RuntimeError,'writer/owner/command'):
            self.supervisor_proof()

    def test_complete_preparation_source_union(self):
        path=self.root/'extra.py';path.write_bytes(b'extra source\n');rows={str(path):self.row(path)}
        proof=audit.preparation_source_equality(rows,copy.deepcopy(rows))
        self.assertEqual(proof['files'],1)
        self.assertEqual(proof['table_sha256'],hashlib.sha256(audit.encoded(rows)).hexdigest())

    def test_missing_preparation_source_rejected(self):
        rows={str(self.source):self.row(self.source)}
        with self.assertRaisesRegex(RuntimeError,'omitted or relabeled'):
            audit.preparation_source_equality(rows,{})

    def test_preparation_typed_row_change_rejected(self):
        rows={str(self.source):self.row(self.source)};changed=copy.deepcopy(rows)
        changed[str(self.source)]['identity']['nlink']=True
        self.assertEqual(rows[str(self.source)]['identity']['nlink'],1)
        with self.assertRaisesRegex(RuntimeError,'omitted or relabeled'):
            audit.preparation_source_equality(rows,changed)

    def invocation(self, original, retained, *, bad_hash=False):
        source=self.root/'original.json';source.write_bytes(original)
        (self.preparation/'invocation.json').write_bytes(retained)
        reference=dict(path=str(source),sha256='0'*64 if bad_hash else self.sha(source))
        io=access.Access({str(source):self.row(source)},output_roots=[self.preparation])
        return audit.preparation_invocation_readback(io,self.preparation,reference)

    def test_reserialized_invocation_preserves_both_raw_hashes(self):
        original=b'{\n  "phase": "preflight", "count": 1\n}\n'
        retained=b'{"count":1,"phase":"preflight"}\n'
        proof=self.invocation(original,retained)
        self.assertTrue(proof['complete_typed_equality'])
        self.assertFalse(proof['same_raw_bytes'])
        self.assertEqual(proof['original']['sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(proof['retained']['sha256'],hashlib.sha256(retained).hexdigest())

    def test_changed_retained_invocation_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'changed typed JSON'):
            self.invocation(b'{"phase":"preflight"}',b'{"phase":"installation"}')

    def test_boolean_cannot_replace_integer_in_retained_invocation(self):
        with self.assertRaisesRegex(RuntimeError,'changed typed JSON'):
            self.invocation(b'{"count":1}',b'{"count":true}')

    def test_original_invocation_hash_must_match_external_reference(self):
        with self.assertRaisesRegex(RuntimeError,'original preparation invocation'):
            self.invocation(b'{}',b'{}',bad_hash=True)


RESOURCE_TEST_SOURCES = {'/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/custom_compiler.py': 'c6a44c3d271664de2c97bf6c3af3ea6426eba6dd3730ac0612411230a02b7449',
 '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/runtime_compiler.py': 'f38cdfd9e9c719185d9e002abf76a8883ad718b3771c62a9788f6feedd52a61b',
 '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/workflow_io.py': 'c159a3152a0019e0d9ebe189ca4b1c48927cc45623d729ed3fd6edf0b13c2acb',
 '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-installation-after-preflight05-03/controller.py': 'ba41563fed996c39c4f082e157c10845ddfca8bbde627ac22a22920c3f0ef642'}


class InstallationResourceTests(unittest.TestCase):
    """Real pure identity and budget code with in-memory fixture documents.

    No fixture file is a real provider, runtime prefix or success receipt. These
    cases exercise the new saved-document seam; no installation is constructed.
    """
    @classmethod
    def setUpClass(cls):
        import sys
        from contextlib import contextmanager
        @contextmanager
        def aliases(values):
            previous={name:sys.modules.get(name) for name in values}
            sys.modules.update(values)
            try:yield
            finally:
                for name,value in previous.items():
                    if value is None:sys.modules.pop(name,None)
                    else:sys.modules[name]=value
        def load(name,path,dependencies=None):
            source=path.read_bytes()
            if hashlib.sha256(source).hexdigest()!=RESOURCE_TEST_SOURCES[str(path)]:
                raise AssertionError('real pure resource test source changed')
            spec=importlib.util.spec_from_file_location('resource_tail_'+name,path)
            module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
            with aliases(dependencies or {}):spec.loader.exec_module(module)
            return module
        custom=load('custom',audit.R/'scripts/custom_compiler.py')
        workflow=load('workflow',audit.R/'scripts/workflow_io.py')
        cls.runtime=load('runtime',audit.R/'scripts/runtime_compiler.py',
            {'custom_compiler':custom,'workflow_io':workflow})
        cls.controller=load('budget',audit.ATTEMPT/'controller.py')

    def setUp(self):
        host='aarch64-apple-darwin';commit='1'*40
        def row(mode=0o444):return dict(sha256='a'*64,size=4097,mode=mode)
        native={'bin/rustc':row(0o555),'lib/librustc_driver-fixture.dylib':row(),
            'lib/libsupport-fixture.dylib':row()}
        native.update({'bin/fixture'+str(i):row(0o555) for i in range(7)})
        native.update({'lib/rustlib/'+host+'/lib/lib'+name+'-fixture.rlib':row()
            for name in ['core','alloc','std','test','proc_macro']})
        sources={name:row() for name in self.runtime.REQUIRED_SOURCES}
        images=[name for name,value in native.items() if value['mode']&0o111 or name.endswith('.dylib')]
        self.spec=dict(schema_version=1,loader_policy=self.runtime.LOADER_POLICY,host=host,
            provenance=dict(source_commit=commit,source_checkout='/fixture/source',
                build_receipt_sha256='b'*64,qualification_receipt_sha256='c'*64,bootstrap_sha256='d'*64),
            compiler='rustc fixture\ncommit-hash: '+commit+'\nhost: '+host+'\n',
            unstable_options=self.runtime.option_proof(' -Z fixture-option = fixture\n'),
            prepublication_qualification=dict(policy='fixture-final'),
            components=[dict(role='runtime',root='/fixture/native',destination='',files=native,links={}),
                dict(role='source',root='/fixture/source',destination=self.runtime.SOURCE.rstrip('/'),
                    files=sources,links={},source_receipt_sha256='e'*64)],
            loader={name:dict(rpaths=[],loads=[]) for name in images})
        self.identity=self.runtime.identity_for(self.spec)
        key=self.runtime.digest(self.identity);self.directory=audit.R/'.work/runtime-compilers'/key
        snapshots=[dict(files={name:[1,index+10,0o100000|row['mode'],row['size'],4,5,1]
            for index,(name,row) in enumerate(component['files'].items())},links={},
            directories={'.':[1,3,0o40555,64,4,5,1]}) for component in self.spec['components']]
        self.admission=dict(identity=copy.deepcopy(self.identity),snapshots=snapshots)
        self.spec_path=str(audit.ATTEMPT/'installation-plan-01/specification.json')
        self.documents={self.spec_path:self.spec,str(self.directory/'admission.json'):self.admission}
        self.plan=dict(specification=dict(path=self.spec_path,sha256=self.sha(self.spec_path)),
            runtime_key=key,sysroot=str(self.directory/'sysroot'),
            installation_resources=self.controller.copy_budget(self.spec,self.identity,snapshots,directory=self.directory))
        self.accessed=[]

    def sha(self,path):return hashlib.sha256(audit.encoded(self.documents[str(path)])).hexdigest()
    def read(self,path):
        self.accessed.append(str(path));return copy.deepcopy(self.documents[str(path)])
    def check(self):
        return audit.installation_resource_readback(self.plan,runtime=self.runtime,
            copy_budget=self.controller.copy_budget,read_json=self.read,sha=self.sha)

    def test_real_identity_and_complete_resource_budget(self):
        before=copy.deepcopy((self.plan,self.documents))
        summary=self.check()
        self.assertEqual(summary,self.plan['installation_resources'])
        self.assertEqual((self.plan,self.documents),before)
        self.assertEqual(self.accessed,[self.spec_path,str(self.directory/'admission.json')])
        self.assertEqual(summary['loader_children'],10);self.assertEqual(summary['total_children'],15)
        self.assertEqual(summary['rounded_payload_bytes'],summary['copied_files']*8192)
        self.assertEqual(summary['admission_json_bytes'],len((json.dumps(self.admission,indent=2,allow_nan=False)+'\n').encode()))
        self.assertEqual(summary['total_reserved_bytes'],sum(summary[k] for k in
            ['rounded_payload_bytes','directory_reservation_bytes','metadata_reservation_bytes','atomic_temporary_reservation_bytes'])+64*2**20)

    def test_resource_specification_hash_is_checked(self):
        self.plan['specification']['sha256']='0'*64
        with self.assertRaisesRegex(RuntimeError,'specification'):self.check()
        self.assertEqual(self.accessed,[])

    def test_resource_specification_route_cannot_substitute_another_document(self):
        other='/fixture/other.json';self.documents[other]=copy.deepcopy(self.spec)
        self.plan['specification']['path']=other
        with self.assertRaisesRegex(RuntimeError,'specification'):self.check()
        self.assertEqual(self.accessed,[])

    def test_resource_key_and_prefix_are_derived_before_admission_access(self):
        original=copy.deepcopy(self.plan)
        for key,value in [('runtime_key','0'*64),('sysroot','/fixture/unowned/sysroot')]:
            self.plan=copy.deepcopy(original);self.plan[key]=value;self.accessed=[]
            with self.subTest(key=key),self.assertRaisesRegex(RuntimeError,'resource (key|prefix)'):self.check()
            self.assertEqual(self.accessed,[self.spec_path])

    def test_resource_admission_identity_cannot_reuse_original_summary(self):
        self.admission['identity']['files']['bin/rustc']='0'*64
        with self.assertRaisesRegex(RuntimeError,'admission identity'):self.check()

    def test_resource_admission_schema_requires_exact_identity_and_snapshots(self):
        self.admission['unexpected']=False
        with self.assertRaisesRegex(RuntimeError,'admission identity'):self.check()

    def test_resource_snapshot_membership_and_stat_types_are_rechecked(self):
        saved=copy.deepcopy(self.admission['snapshots'])
        for defect in ['missing','extra','bool','size','mode']:
            self.admission['snapshots']=copy.deepcopy(saved);snap=self.admission['snapshots'][0]
            if defect=='missing':snap['files'].pop('bin/rustc')
            elif defect=='extra':snap['links']['extra']=[1]*7
            elif defect=='bool':snap['files']['bin/rustc'][0]=True
            elif defect=='size':snap['files']['bin/rustc'][3]+=1
            else:snap['files']['bin/rustc'][2]=0o100444
            with self.subTest(defect=defect),self.assertRaises(RuntimeError):self.check()

    def test_matching_forged_plan_and_terminal_budget_cannot_bypass_recomputation(self):
        self.plan['installation_resources']['total_reserved_bytes']+=4096
        terminal=dict(installation_resources=copy.deepcopy(self.plan['installation_resources']))
        self.assertEqual(terminal['installation_resources'],self.plan['installation_resources'])
        with self.assertRaisesRegex(RuntimeError,'recomputed'):self.check()

    def test_truthy_or_partial_budget_cannot_be_accepted(self):
        original=copy.deepcopy(self.plan['installation_resources'])
        for forged in [True,{'total_reserved_bytes':original['total_reserved_bytes']}]:
            self.plan['installation_resources']=forged
            with self.subTest(forged=forged),self.assertRaisesRegex(RuntimeError,'recomputed'):self.check()


class ProviderDirectoryTests(unittest.TestCase):
    """Actual helper/Access with owned empty directories, never provider inputs."""
    def setUp(self):
        import os
        self.os = os
        self.tmp = tempfile.TemporaryDirectory(prefix='saved-provider-directories-')
        self.addCleanup(self.tmp.cleanup)
        self.owner = Path(self.tmp.name).resolve()
        self.root = self.owner/'provider'; self.root.mkdir()
        self.lib = self.root/'lib'; self.lib.mkdir()
        self.nested = self.lib/'nested'; self.nested.mkdir()
        self.empty = self.lib/'empty'; self.empty.mkdir()
        self.payload = self.nested/'payload'; self.payload.write_bytes(b'owned payload\n')
        self.link = self.lib/'alias'; self.link.symlink_to('nested/payload')
        self.fields = ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')
        def saved(path):
            row = access.stamp(path.lstat())
            return [row[key] for key in self.fields]
        self.saved = saved
        self.component = dict(root=str(self.root),files={'lib/nested/payload':{}},links={'lib/alias':{}})
        self.spec = dict(components=[self.component])
        self.snapshot = dict(files={'lib/nested/payload':saved(self.payload)},links={'lib/alias':saved(self.link)},
            directories={'.':saved(self.root),'lib':saved(self.lib),'lib/nested':saved(self.nested),
                         'lib/empty':saved(self.empty)})
        self.admission = dict(identity=dict(admission=copy.deepcopy(self.spec),fixture=True),
                              snapshots=[self.snapshot])
        key = hashlib.sha256(audit.encoded(self.admission['identity'])[:-1]).hexdigest()
        sysroot = str(self.owner/'.work/runtime-compilers'/key/'sysroot')
        self.plan = dict(owner=str(self.owner),phase='installation',runtime_key=key,sysroot=sysroot)
        self.terminal = dict(phase='installation',status='passed',runtime_key=key,installed_runtime_key=key,sysroot=sysroot)
        self.ready = dict(status='installed',owner=str(self.owner),key=key,sysroot=sysroot,
                          identity=copy.deepcopy(self.admission['identity']))
        self.files = {str(self.payload):dict(size=self.payload.stat().st_size,
            sha256=hashlib.sha256(self.payload.read_bytes()).hexdigest(),identity=access.stamp(self.payload.lstat()))}
        self.links = {str(self.link):dict(stamp=saved(self.link),target='nested/payload',resolved=str(self.payload))}
        self.observed = []

    def identity(self, name):
        self.observed.append(name)
        with access.parent_descriptor(name) as (parent,leaf):
            return access.stamp(self.os.stat(leaf,dir_fd=parent,follow_symlinks=False))

    def derive(self):
        return audit.admitted_provider_directories(self.plan,self.spec,self.terminal,self.ready,self.admission,
            files=self.files,links=self.links,identity=self.identity,path_check=access.path,
            typed_identity=access.typed_identity)

    def test_empty_directory_declared_without_byte_or_descendant_scope(self):
        old = access.Access(self.files,entries={str(p):access.stamp(p.lstat()) for p in [self.root,self.lib,self.nested]})
        with self.assertRaisesRegex(RuntimeError,'undeclared saved-evidence'):
            old.identity(self.empty)
        before = copy.deepcopy((self.plan,self.spec,self.terminal,self.ready,self.admission,self.files,self.links))
        proof = self.derive(); io = access.Access(self.files,entries=proof['entries'])
        self.assertEqual(io.identity(self.empty),access.stamp(self.empty.lstat()))
        self.assertEqual(proof['components'],[dict(root=str(self.root),directories=4,
            required_ancestors=3,additional_declared_directories=1)])
        self.assertEqual(set(self.observed),set(proof['entries']))
        self.assertEqual(before,(self.plan,self.spec,self.terminal,self.ready,self.admission,self.files,self.links))
        for path in [self.empty,self.root/'unlisted',self.empty/'child']:
            with self.subTest(path=path),self.assertRaisesRegex(RuntimeError,'undeclared saved-evidence'):
                io.read_bytes(path)
        with self.assertRaisesRegex(RuntimeError,'undeclared saved-evidence'):
            io.identity(self.root/'unlisted')

    def test_missing_root_or_payload_link_ancestor_rejected_before_observation(self):
        original = copy.deepcopy(self.snapshot['directories'])
        for name in ['.','lib','lib/nested']:
            self.snapshot['directories'] = copy.deepcopy(original);del self.snapshot['directories'][name]
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'omit root or payload/link ancestor'):
                self.derive()
            self.assertEqual(self.observed,[])

    def test_unsafe_relative_names_and_component_roots_rejected(self):
        original = copy.deepcopy(self.snapshot['directories'])
        for name in ['../escape','/outside','lib//empty','lib/./empty','lib/../empty','lib\\empty','lib/\x00empty']:
            self.snapshot['directories'] = copy.deepcopy(original)
            self.snapshot['directories'][name] = self.saved(self.empty)
            with self.subTest(name=name),self.assertRaisesRegex(RuntimeError,'canonical relative'):
                self.derive()
            self.assertEqual(self.observed,[])
        self.snapshot['directories'] = original
        self.component['root'] = str(self.root)+'/../provider'
        # Rebind only the synthetic fixture identity so canonical-root validation is reached.
        self.admission['identity']['admission'] = copy.deepcopy(self.spec)
        self.ready['identity'] = copy.deepcopy(self.admission['identity'])
        key = hashlib.sha256(audit.encoded(self.admission['identity'])[:-1]).hexdigest()
        for doc in [self.plan,self.terminal]:doc['runtime_key'] = key;doc['sysroot'] = str(self.owner/'.work/runtime-compilers'/key/'sysroot')
        self.terminal['installed_runtime_key'] = self.ready['key'] = key;self.ready['sysroot'] = self.plan['sysroot']
        with self.assertRaisesRegex(RuntimeError,'canonical absolute'):
            self.derive()

    def test_malformed_or_non_directory_saved_stamp_rejected(self):
        saved = self.saved(self.empty)
        variants = [saved[:-1], [True,*saved[1:]], [*saved[:1],0,*saved[2:]],
                    [*saved[:2],self.files[str(self.payload)]['identity']['mode'],*saved[3:]],
                    [*saved[:3],-1,*saved[4:]]]
        for row in variants:
            self.snapshot['directories']['lib/empty'] = row
            with self.subTest(row=row),self.assertRaises(RuntimeError):self.derive()
            self.assertEqual(self.observed,[])

    def test_unbacked_file_link_and_payload_directory_collision_rejected(self):
        original_files = copy.deepcopy(self.files);original_links = copy.deepcopy(self.links)
        self.files = {}
        with self.assertRaisesRegex(RuntimeError,'file is outside'):self.derive()
        self.files = original_files;self.links = {}
        with self.assertRaisesRegex(RuntimeError,'link is outside'):self.derive()
        self.links = original_links
        self.snapshot['directories']['lib/nested/payload'] = self.saved(self.empty)
        with self.assertRaisesRegex(RuntimeError,'collides with frozen payload/link'):self.derive()
        self.assertEqual(self.observed,[])

    def test_directory_changed_before_observation_rejected(self):
        self.empty.chmod((self.empty.lstat().st_mode & 0o7777) ^ 0o100)
        with self.assertRaisesRegex(RuntimeError,'admitted provider directory changed'):self.derive()

    def test_directory_changed_after_scope_rejected_by_unchanged_access(self):
        proof = self.derive();io = access.Access(self.files,entries=proof['entries'])
        io.identity(self.empty)
        self.empty.chmod((self.empty.lstat().st_mode & 0o7777) ^ 0o100)
        with self.assertRaisesRegex(RuntimeError,'declared entry identity differs'):io.identity(self.empty)

    def test_passed_keyed_authority_and_complete_snapshot_required(self):
        original = copy.deepcopy((self.plan,self.spec,self.terminal,self.ready,self.admission))
        for defect in ['failed','key','spec','ready','snapshot','file-membership']:
            self.plan,self.spec,self.terminal,self.ready,self.admission = copy.deepcopy(original)
            if defect == 'failed':self.terminal['status']='failed'
            elif defect == 'key':self.plan['runtime_key']='0'*64
            elif defect == 'spec':self.spec['unexpected']=True
            elif defect == 'ready':self.ready['identity']['fixture']=False
            elif defect == 'snapshot':self.admission['snapshots']=[]
            else:self.admission['snapshots'][0]['files']={}
            with self.subTest(defect=defect),self.assertRaises(RuntimeError):self.derive()
            self.assertEqual(self.observed,[])

    def test_directory_replaced_by_symlink_is_not_followed(self):
        target = self.owner/'other';target.mkdir()
        self.empty.rmdir();self.empty.symlink_to(target,target_is_directory=True)
        # The owned replacement changes its parent too; retain that new parent
        # stamp so this fixture reaches the forbidden symlink leaf itself.
        self.snapshot['directories']['lib'] = self.saved(self.lib)
        with self.assertRaisesRegex(RuntimeError,'entry kind differs'):self.derive()


if __name__ == '__main__':
    unittest.main()

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage2_continuation', ROOT/'experiments/hir-stage2-package/check.py')
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)


def result(count, filtered=0):
    return f'test result: ok. {count} passed; 0 failed; 0 ignored; 0 measured; {filtered} filtered out; finished in 1s\n'


class Stage2ContinuationTests(unittest.TestCase):
    def test_failed_native_build_only_or_missing_hits_cannot_admit(self):
        plan = dict(sha256='a'*64, value={'previous': {'source': {'revision': 'b'*40}}})
        row = dict(status='passed', stage='run', owner=str(m.NATIVE), expected_plan_sha256='a'*64,
            source_revision='b'*40, capacity=copy.deepcopy(m.native.CAPACITY), bootstrap_commands_passed=3,
            actual_option_tests_passed=1, actual_native_runmake_passed=1, required_units_prerequisite=26,
            final_artifacts_sha256='c'*64, started_at=1, admitted_at=2, finished_at=3)
        m.checked_native_terminal(row, plan, 'c'*64)
        for key,value in [('status','failed'),('actual_native_runmake_passed',0),('bootstrap_commands_passed',1),
                          ('source_revision','d'*40),('required_units_prerequisite',22),('admitted_at',4)]:
            bad=copy.deepcopy(row); bad[key]=value
            with self.assertRaises(RuntimeError): m.checked_native_terminal(bad,plan,'c'*64)
        with self.assertRaises(RuntimeError): m.checked_native_terminal(row,plan,'d'*64)
        with self.assertRaises(RuntimeError): m.native.checked_native(
            'test [run-make] tests/run-make/hir-body-cache-capture ... ok\n'+result(1))

    def test_reviewed_plan_rejects_rehashed_scope_capacity_and_test_drops(self):
        frozen={'helper':'a'*64}; names=['unit']
        plan=dict(owner=str(m.ROOT),source=str(m.SOURCE),checkpoint=m.native.CHECKPOINT,inputs=frozen,
            required_units=names,commands=copy.deepcopy(m.COMMANDS),probes=copy.deepcopy(m.PROBES),
            capacity=copy.deepcopy(m.CAPACITY),actions=list(m.ACTIONS),canonical_lock=str(m.engine.CANONICAL_LOCK),run_attempt='run-01')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve()/'plan.json'; path.write_text(json.dumps(plan)); reviewed=m.sha(path)
            self.assertEqual(m.load_plan(path,reviewed,frozen,names),plan)
            changes=[]
            bad=copy.deepcopy(plan); bad['commands']['stage2-units'].append('--test-args'); changes.append(bad)
            bad=copy.deepcopy(plan); bad['commands']['stage2-hir'].remove('--no-capture'); changes.append(bad)
            bad=copy.deepcopy(plan); bad['capacity']['initial_free_gib']=16; changes.append(bad)
            bad=copy.deepcopy(plan); bad['capacity']['running_floor_gib']=1; changes.append(bad)
            bad=copy.deepcopy(plan); bad['actions'].remove('strip6'); changes.append(bad)
            bad=copy.deepcopy(plan); bad['canonical_lock']='/tmp/other.lock'; changes.append(bad)
            bad=copy.deepcopy(plan); bad['run_attempt']='../old'; changes.append(bad)
            for bad in changes:
                path.write_text(json.dumps(bad))
                for digest in [reviewed,m.sha(path)]:
                    with self.assertRaises(RuntimeError): m.load_plan(path,digest,frozen,names)

    def test_native_child_raw_bytes_and_returncode_are_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp).resolve(); directory=parent/'commands/000'; directory.mkdir(parents=True)
            stdout=directory/'stdout'; stderr=directory/'stderr'; stdout.write_text('actual output'); stderr.write_text('')
            path=directory/'receipt.json'; command=['./x','build']
            row=dict(status='finished',returncode=0,command=command,stdout_sha256=m.sha(stdout),stderr_sha256=m.sha(stderr))
            path.write_text(json.dumps(row)); ref=dict(path=str(path),sha256=m.sha(path),command=command)
            files={}; self.assertEqual(m.read_child(ref,parent,files)[1],'actual output'); self.assertEqual(len(files),3)
            stdout.write_text('forged output')
            with self.assertRaises(RuntimeError): m.read_child(ref,parent,{})
            stdout.write_text('actual output'); row['returncode']=1; path.write_text(json.dumps(row)); ref['sha256']=m.sha(path)
            with self.assertRaises(RuntimeError): m.read_child(ref,parent,{})

    def test_full_existing_partition_suites_and_all_twenty_six_units_remain_required(self):
        text=''.join(f'test [codegen-units] tests/codegen-units/partitioning/test{i}.rs ... ok\n' for i in range(15))+result(15,33)
        for name in ['stable-cgu-partitioning','stable-mono-cgu-partitioning']:
            text+=f'test [run-make] tests/run-make/{name} ... ok\n'
        text+=result(2,528); m.checked_partition(text)
        with self.assertRaises(RuntimeError): m.checked_partition(text.replace('test14.rs ... ok','test14.rs ... ignored'))
        with self.assertRaises(RuntimeError): m.checked_partition(text.replace('stable-mono-cgu-partitioning','unrelated'))
        names=m.native.checkpoint()[1]
        units=''.join(f'test body_cache::{name} ... ok\n' for name in names)+result(26)
        m.engine.checked_tests(units,names,[]); m.native.checked_result(units,26,unfiltered=True)
        with self.assertRaises(RuntimeError): m.native.checked_result(units.replace('0 filtered out','1 filtered out'),26,unfiltered=True)
        with self.assertRaises(RuntimeError): m.engine.checked_tests(units.replace(names[-1],'unrelated'),names,[])

    def test_actual_stage2_and_packaged_capabilities_are_both_required(self):
        root=Path('/owned/stage2'); revision='c'*40
        rows=[dict(stdout='commit-hash: '+revision+'\n'),dict(stdout=str(root)+'\n'),dict(stdout=''.join(
            '    -Z '+name+'=val\n' for name in ['stable-cgu-partitioning','stable-mono-cgu-partitioning','hir-body-cache-capture','hir-body-cache-reuse']))]
        m.probe_identity(rows,root,revision)
        for old,new in [('hir-body-cache-reuse','unrelated'),('stable-mono-cgu-partitioning','unrelated')]:
            bad=copy.deepcopy(rows); bad[2]['stdout']=bad[2]['stdout'].replace(old,new)
            with self.assertRaises(RuntimeError): m.probe_identity(bad,root,revision)
        with self.assertRaises(RuntimeError): m.probe_identity(rows,Path('/another/prefix'),revision)
        with self.assertRaises(RuntimeError): m.probe_identity(rows,root,'d'*40)

    def test_typed_source_inventory_does_not_relabel_links_as_source_bytes(self):
        files={'library/core/src/lib.rs':dict(kind='file',sha256='a'*64),
               'library/backtrace':dict(kind='gitlink',object='b'*40),
               'src/link':dict(kind='symlink',target='other')}
        self.assertEqual(m.package.ordinary_files(files),{'library/core/src/lib.rs':'a'*64})
        for records in [{'../escape':dict(kind='file',sha256='a'*64)},
                        {'x':dict(kind='file',sha256='bad')}, {'x':dict(kind='directory',sha256='a'*64)}]:
            with self.assertRaises(RuntimeError): m.package.ordinary_files(records)

if __name__=='__main__': unittest.main()

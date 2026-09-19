"""Bounded read-only native reconciliation discovery; separate review before use.

Preserves the full immutable native03 base and freezes only a compact delta.
Does not construct the controller, create WORK, or execute provider commands.
"""
import ast
import json
import os
from pathlib import Path
import shutil
import sys
import time

import run as n

MAXIMUM_DELTA_FILES=2048
MAXIMUM_DELTA_BYTES=512*2**20
SOURCE_NAMES={'SCHEMA.md','run.py','prepare.py','readback.py','readback-from-failure-audit.diff',
    'parser_controls.py','parser-controls-from-loader09.diff','wrong_beta.py','test_wrong_beta.py',
    'parser-source-proof.json'}


def publish(path,value):
    data=n.encoded(value)
    n.require(len(data)<=n.LIMITS['maximum_document_bytes'],'bounded proposal document required')
    with Path(path).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    n.require(n.file(path)['sha256']==n.hashlib.sha256(data).hexdigest(),'proposal publication readback differs')


class Discovery:
    def __init__(self):
        n.require(n.file(n.ORIGINAL_SOURCE/'inputs.json')['sha256']==n.BASE_SHA,'exact native03 base required')
        self.base=n.read(n.ORIGINAL_SOURCE/'inputs.json')
        self.files=dict(self.base['files']);self.delta={};self.routes={};self.memberships={};self.selected=set()
        self.total=0;self.started=time.monotonic();self.last_sample=0;self.samples=[]
        self.original=n.read(n.ORIGINAL_SOURCE/'plan.json')
        n.file(n.ORIGINAL_SOURCE/'plan.json',self.files[str(n.ORIGINAL_SOURCE/'plan.json')])
        self.roots=sorted(set(self.original['evidence_roots'])|{str(n.WORK)})
        self.owned=n.module('owned_stage',n.OWNED,self.files)
        self.monitor=n.module('reconciliation_preparation_monitor',n.MONITOR,self.files)

    def guard(self):
        n.require(shutil.disk_usage(n.A).free>=9*2**30,'read-only discovery free space below9GiB')
        n.require(time.monotonic()-self.started<=600,'bounded discovery deadline exceeded')
        if time.monotonic()-self.last_sample>=5:
            row=self.monitor.sample(evidence_root=n.WORK,evidence_roots=list(map(Path,self.roots)))
            n.require(self.monitor.rejection(row) is None,'discovery aggregate capacity rejected')
            self.samples.append(row);self.last_sample=time.monotonic()

    def add(self,path,*,retain=True):
        self.guard();path=Path(path);resolved=path.resolve(strict=True)
        self.routes[str(path)]=str(resolved)
        value=n.file(resolved,self.files.get(str(resolved)),self.guard)
        if str(resolved) not in self.base['files']:
            if str(resolved) not in self.delta:self.total+=value['size']
            self.delta[str(resolved)]=value
            n.require(len(self.delta)<=MAXIMUM_DELTA_FILES and self.total<=MAXIMUM_DELTA_BYTES,
                      'bounded compact delta discovery exceeded')
            if retain:
                n.require(value['size']<=n.LIMITS['maximum_file_bytes'],'selected delta source exceeds1MiB')
                self.selected.add(str(resolved))
        self.files[str(resolved)]=value
        return resolved

    def tree(self,root,*,original_payload=False):
        root=Path(root)
        n.require(root.resolve(strict=True)==root and root.is_dir() and not root.is_symlink(),
                  'ordinary closed evidence root required')
        entries={}
        for path in sorted(root.rglob('*')):
            self.guard();n.require(not path.is_symlink(),'indirect closed evidence entry')
            name=str(path.relative_to(root));entries[name]='directory' if path.is_dir() else 'file'
            n.require(len(entries)<=1024,'bounded closed evidence membership')
            if path.is_dir():continue
            keep=not original_payload or path.parent not in [root/'source-snapshots',root/'artifacts']
            self.add(path,retain=keep)
        self.memberships[str(root)]=entries

    def discover(self):
        # Complete original current-byte validation is retained despite compact
        # catalog representation. This scan never invokes an original controller.
        n.verify_inputs(self.base,self.guard)
        self.add(n.ORIGINAL_SOURCE/'inputs.json',retain=False)
        for path in sorted(n.ORIGINAL_SOURCE.iterdir()):
            if path.name!='inputs.json':self.add(path)
        self.tree(n.ORIGINAL_WORK,original_payload=True)
        for root in [n.A/'.work/experiments/hir-options-hash-native-controls-supervisor-03',
                     n.A/'.work/native-controls-launch-execution-03',
                     n.A/'.work/native-controls-failure-verification-execution-03',
                     n.A/'.work/native-controls-failure-verification-execution-03-pid-reuse-01']:
            self.tree(root)
        for name in ['launch_native_controls_03.py','verify_native_controls_03.py',
                     'verify_native_controls_failure_03.py','verify_native_controls_failure_03.diff',
                     'verify_native_controls_failure_03_pid_reuse_01.py',
                     'verify_native_controls_failure_03_pid_reuse_01.diff',
                     'native-controls-failure-verification-03.json']:
            self.add(n.A/'.work'/name)
        n.failure_audit(self.add)
        n.require({p.name for p in n.HERE.iterdir()}==SOURCE_NAMES,'fresh reviewed reconciliation source membership differs')
        for name in sorted(SOURCE_NAMES):
            path=self.add(n.HERE/name)
            if path.suffix=='.py':ast.parse(path.read_bytes(),filename=str(path))
        controls=n.module('reconciliation_discovery_parser_controls',n.HERE/'parser_controls.py',self.files)
        for path in sorted(controls.CONTROL.iterdir()):self.add(path)
        control_freeze=n.read(controls.CONTROL/'inputs.json')
        for name,resolved in control_freeze['routes'].items():
            n.require(str(Path(name).resolve(strict=True))==resolved,'tested control input route changed')
            self.routes[name]=resolved
        # validate() calls add for all24 frozen inputs, every raw receipt,
        # dispatcher/auditor source and the actual successful audit execution.
        proof=controls.validate(self.add,self.files)
        for root in [controls.WORK,controls.OUTER,controls.LAUNCHER,
                     n.A/'.work/native-wrong-beta-controls-verification-execution-01']:
            self.tree(root)
        original_receipt=n.read(n.ORIGINAL_WORK/'receipt.json')
        command,reconciliation=n.provenance(self.original,original_receipt,proof,self.files)
        library,providers=n.beta_providers(self.original,self.files)
        plan=dict(self.original,read_only_reconciliation=True,actual_workload_children=0,
            base_inputs=reconciliation['base_inputs'],command_evidence=command,reconciliation=reconciliation,
            wrong_beta_providers=providers,wrong_beta_lib=library,reconciliation_evidence_roots=self.roots)
        python=self.add(Path(sys.executable).resolve(strict=True))
        self.add('/opt/homebrew/bin/python3');self.add(n.A/'scripts/supervise_experiment.py')
        n.require(str(python)==self.base['python'],'original qualified Python executor required')
        freeze=dict(base_inputs=reconciliation['base_inputs'],files=self.delta,links={},
            absent_paths=[str(n.ORIGINAL_WORK/'native-controls.json')],routes=self.routes,
            memberships=self.memberships,python=str(python),launch_environment=self.original['environment'],
            retention_limits=n.LIMITS,retained_delta_inputs=sorted(self.selected),
            retained_reference_proofs=dict(original_manifest=str(n.ORIGINAL_WORK/'source-snapshots.json'),
                original_projection=str(n.ORIGINAL_SOURCE/'snapshot-plan.json'),
                original_physical_directory=str(n.ORIGINAL_WORK/'source-snapshots'),
                original_retained_artifacts=str(n.ORIGINAL_WORK/'artifacts'),
                failure_audit=dict(path=str(n.FAILURE_AUDIT),sha256=n.FAILURE_SHA),
                policy='Full original239logical/179gzip plus4 retained artifacts stay in their counted original root; standalone retention must include every referenced payload.'))
        return plan,freeze


def main():
    n.require(Path.cwd()==n.A and sys.dont_write_bytecode and not sys.flags.optimize,
              'fixed owner and unoptimized Python -B required')
    n.require(not n.WORK.exists() and not n.WORK.is_symlink()
        and not any((n.HERE/name).exists() for name in ['plan.json','inputs.json','metadata-preflight.json','launch.json']),
        'fresh read-only preparation namespace required')
    discovery=Discovery()
    with discovery.owned.workload_lock(discovery.owned.CANONICAL_LOCK,600):
        discovery.owned.disk(n.A,16)
        started=time.time();plan,freeze=discovery.discover()
        publish(n.HERE/'plan.json',plan)
        value=n.file(n.HERE/'plan.json');freeze['files'][str(n.HERE/'plan.json')]=value
        freeze['retained_delta_inputs']=sorted([*freeze['retained_delta_inputs'],str(n.HERE/'plan.json')])
        freeze['plan_sha256']=value['sha256'];publish(n.HERE/'inputs.json',freeze)
        projection=n.retention_projection(freeze)
        sample=discovery.monitor.sample(evidence_root=n.WORK,evidence_roots=list(map(Path,plan['reconciliation_evidence_roots'])))
        n.require(discovery.monitor.rejection(sample) is None
            and sample['evidence_allocated_bytes']+projection['projected_reservation_bytes']<=256*2**20,
            'delta retention plus32MiB remaining reserve exceeds aggregate evidence cap')
        # Revalidate all newly admitted delta bytes and all original stamps after
        # discovery. The original full bytes were read above under this lock.
        n.verify_inputs(dict(files=freeze['files'],links={},absent_paths=freeze['absent_paths']),discovery.guard)
        for path,row in discovery.base['files'].items():
            discovery.guard();n.require(n.identity(path)==row['identity'],'original input changed during preparation')
        publish(n.HERE/'metadata-preflight.json',dict(status='passed',started_at=started,finished_at=time.time(),
            workload_children=0,work_created=False,full_original_input_hashes=True,
            base_files=len(discovery.base['files']),base_bytes=sum(r['size'] for r in discovery.base['files'].values()),
            delta_files=len(freeze['files']),delta_bytes=sum(r['size'] for r in freeze['files'].values()),
            retained_delta_files=len(projection['files']),retained_delta_logical_bytes=projection['logical_bytes'],
            retained_delta_allocated_bytes=projection['projected_allocated_bytes'],
            projected_reservation_bytes=projection['projected_reservation_bytes'],capacity=sample,
            inputs_sha256=n.file(n.HERE/'inputs.json')['sha256']))
        launch=dict(owner=str(n.A),environment=freeze['launch_environment'],expected_children=0,
            read_only_reconciliation=True,capacity=dict(entry_gib=16,stop_gib=9,floor_gib=8,
                namespace_bytes=14*2**30,evidence_bytes=256*2**20),
            command=[freeze['python'],'-B',str(n.A/'scripts/supervise_experiment.py'),'--run-id',
                'hir-options-hash-native-controls-reconciliation-supervisor-01','--',freeze['python'],'-B',str(n.HERE/'run.py'),
                '--inputs-sha256',n.file(n.HERE/'inputs.json')['sha256']],
            inputs_sha256=n.file(n.HERE/'inputs.json')['sha256'],plan_sha256=freeze['plan_sha256'],
            metadata_preflight_sha256=n.file(n.HERE/'metadata-preflight.json')['sha256'],
            review_required_before_launch=True)
        publish(n.HERE/'launch.json',launch);discovery.guard()
        print(json.dumps(dict(status='prepared-unrun',launch_sha256=n.file(n.HERE/'launch.json')['sha256'],
            inputs_sha256=launch['inputs_sha256'],delta_files=len(freeze['files']),
            retained_delta_files=len(projection['files']),projected_reservation_bytes=projection['projected_reservation_bytes'])))


if __name__=='__main__':main()

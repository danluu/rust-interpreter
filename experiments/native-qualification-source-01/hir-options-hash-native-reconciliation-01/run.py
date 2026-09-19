"""Zero-command native reconciliation; source proposal pending exact review.

The original native03 process history remains failed and immutable. This reader
replays its complete byte-bound evidence, then applies the separately qualified
wrong-B3 parser. It never starts a compiler, provider probe or native program.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
from types import ModuleType

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = A/'experiments/hir-options-hash-native-reconciliation-01'
WORK = A/'.work/hir-options-hash-native-controls-reconciliation-01'
ORIGINAL_SOURCE = A/'experiments/hir-options-hash-native-controls-03'
ORIGINAL_WORK = A/'.work/hir-options-hash-native-controls-03'
BASE_SHA = '8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d'
FAILURE_AUDIT = A/'.work/native-controls-failure-verification-03.json'
FAILURE_SHA = '1058d64e64d75748a3da12115a8400a01daa5cd499b39b09c8d29520eaab4f24'
ORIGINAL_RECEIPT_SHA = '76fe70afd8eb6486b445e39366de2dd1ffd52ed9578e63203dc7cf74a679a272'
ORIGINAL_ERROR = "ValueError('wrong-B3 failure is not compiler metadata incompatibility')"
MONITOR = A/'experiments/hir-options-hash-stage-monitor/monitor.py'
OWNED = X/'experiments/stable-cgu/owned_stage.py'
FIELDS = ('dev','ino','mode','size','mtime_ns','ctime_ns','nlink')
ADDITIONS = {'read_only_reconciliation','actual_workload_children','base_inputs',
             'command_evidence','reconciliation','wrong_beta_providers',
             'wrong_beta_lib','reconciliation_evidence_roots'}
LIMITS = dict(maximum_files=256,maximum_file_bytes=2**20,maximum_logical_bytes=8*2**20,
              maximum_document_bytes=2*2**20,metadata_reservation_bytes=10*2**20,
              remaining_evidence_reservation_bytes=32*2**20)


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def identity(path):
    value=Path(path).lstat()
    return {name:getattr(value,'st_'+name) for name in FIELDS}


def file(path, expected=None, guard=lambda:None):
    path=Path(path); before=identity(path)
    require(path.is_absolute() and path.resolve(strict=True)==path and stat.S_ISREG(before['mode'])
            and before['size']<=2*2**30, 'bounded ordinary input required')
    digest=hashlib.sha256()
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        require({key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before,
                'opened input identity changed')
        while block:=stream.read(2**20):guard();digest.update(block)
        require({key:getattr(os.fstat(stream.fileno()),'st_'+key) for key in FIELDS}==before,
                'input changed during read')
    require(identity(path)==before,'input identity changed')
    row=dict(size=before['size'],sha256=digest.hexdigest(),identity=before)
    require(expected is None or row==expected,'frozen input differs: '+str(path))
    return row


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key');result[key]=value
    return result


def read(path, limit=64*2**20):
    path=Path(path)
    require(path.stat().st_size<=limit,'bounded JSON required')
    return json.loads(path.read_bytes(),object_pairs_hook=unique,
                      parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))


def module(name,path,files):
    path=Path(path);file(path,files[str(path)])
    data=path.read_bytes()
    require(len(data)==files[str(path)]['size'] and hashlib.sha256(data).hexdigest()==files[str(path)]['sha256']
            and identity(path)==files[str(path)]['identity'],'executed module bytes changed')
    result=ModuleType(name);result.__file__=str(path)
    sys.modules[name]=result
    exec(compile(data,str(path),'exec'),result.__dict__)
    return result


def merged_inputs(freeze):
    require(freeze['base_inputs']==dict(path=str(ORIGINAL_SOURCE/'inputs.json'),sha256=BASE_SHA),
            'exact original native03 base inputs required')
    require(file(ORIGINAL_SOURCE/'inputs.json')['sha256']==BASE_SHA,'base catalog changed')
    base=read(ORIGINAL_SOURCE/'inputs.json'); merged={}
    for key in ['files','links']:
        require(not set(base[key])&set(freeze[key]),'compact delta overlaps immutable base '+key)
        merged[key]=dict(base[key])|freeze[key]
    merged['absent_paths']=sorted(set(base['absent_paths'])|set(freeze['absent_paths']))
    require(str(ORIGINAL_WORK/'native-controls.json') in freeze['absent_paths'],
            'original failed result absence must remain explicit')
    return base,merged


def provenance(original, receipt, controls, files):
    """Exact agreed objects; the failed owner is never replaced by this reader."""
    require(files[str(ORIGINAL_WORK/'receipt.json')]['sha256']==ORIGINAL_RECEIPT_SHA
            and receipt['status']=='failed' and receipt['error']==ORIGINAL_ERROR
            and len(receipt['commands'])==20, 'exact complete failed native03 owner required')
    base=dict(path=str(ORIGINAL_SOURCE/'inputs.json'),sha256=BASE_SHA)
    audit=dict(path=str(FAILURE_AUDIT),sha256=FAILURE_SHA)
    command=dict(source=str(ORIGINAL_SOURCE),evidence=str(ORIGINAL_WORK),
        receipt_sha256=ORIGINAL_RECEIPT_SHA,inputs_sha256=BASE_SHA,
        plan_sha256=files[str(ORIGINAL_SOURCE/'plan.json')]['sha256'],
        snapshot_plan_sha256=files[str(ORIGINAL_SOURCE/'snapshot-plan.json')]['sha256'],
        status='failed',error=ORIGINAL_ERROR,commands=receipt['commands'],failure_audit=audit)
    reconciliation=dict(source=str(HERE),base_inputs=base,
        original_parser=dict(path=str(ORIGINAL_SOURCE/'observations.py'),
            sha256=files[str(ORIGINAL_SOURCE/'observations.py')]['sha256']),
        parser=dict(path=str(HERE/'wrong_beta.py'),sha256=files[str(HERE/'wrong_beta.py')]['sha256']),
        parser_controls=controls,failure_audit=audit)
    return command,reconciliation


def beta_providers(original, files):
    beta=Path(original['namespace'])/'beta-sysroot'
    library=beta/'lib/rustlib/aarch64-apple-darwin/lib'
    inventory_path=Path(original['assembly']['evidence'])/'assembly/output-inventory.json'
    file(inventory_path,files[str(inventory_path)])
    inventory=read(inventory_path); selected=[]
    for name,row in sorted(inventory.items()):
        path=beta/name
        if path.parent==library and re.fullmatch(r'lib(?:std|std_detect|core|compiler_builtins)-[a-f0-9]+\.(?:rmeta|rlib|dylib)',path.name):
            value={key:row[key] for key in ['size','sha256','identity']}
            require(value==files[str(path)], 'B3 inventory provider differs from original frozen bytes')
            selected.append(dict(path=str(path),**value))
    require(len(selected)==9, 'exact complete admitted wrong-beta provider selection required')
    return str(library),selected


def verify_inputs(inputs, guard):
    for name,row in inputs['files'].items():file(name,row,guard)
    for name,row in inputs['links'].items():
        guard();path=Path(name);stamp=[identity(path)[key] for key in FIELDS]
        require(path.is_symlink() and stamp==row['stamp'] and os.readlink(path)==row['target']
                and str(path.resolve(strict=True))==row['resolved'],'frozen source/provider link differs')
    for name in inputs['absent_paths']:
        guard();require(not Path(name).exists() and not Path(name).is_symlink(),'frozen absence changed')


def failure_audit(check):
    audit=read(check(FAILURE_AUDIT))
    require(file(FAILURE_AUDIT)['sha256']==FAILURE_SHA and audit['status']=='verified-retained-failure'
            and audit['receipt_sha256']==ORIGINAL_RECEIPT_SHA and audit['children']==20
            and audit['historical_failed_children']==11 and audit['total_actual_native_children']==31
            and audit['qualified_native_children']==0 and audit['native_roles_and_behavior_qualified'] is False,
            'accepted original retained-failure audit differs')
    execution=A/'.work/native-controls-failure-verification-execution-03-pid-reuse-01'
    source=A/'.work/verify_native_controls_failure_03_pid_reuse_01.py'
    row=read(check(execution/'record.json'))
    require(row['status']=='finished' and row['returncode']==0 and row['source_sha256']==audit['verifier_sha256']
            ==file(check(source))['sha256']=='478de740c68b3d2dea41911b2512754b3c5de22499b2a52eba9dd6d199d4a08e'
            and row['command']==['/opt/homebrew/bin/python3','-B',str(source)] and row['cwd']==str(A)
            and row['started_at']<=audit['started_at']<=audit['finished_at']<=row['finished_at'],
            'actual PID-aware failure-audit execution differs')
    for stream in ['stdout','stderr']:
        require(file(check(execution/stream))['sha256']==row[stream+'_sha256'], 'failure-audit execution raw differs')
    require(not (execution/'stderr').read_bytes() and read(execution/'stdout')==dict(path=str(FAILURE_AUDIT),
            sha256=FAILURE_SHA,children=20,cwd_unavailable=2), 'failure-audit actual publication differs')
    return audit


def retention_projection(freeze):
    require(freeze['retention_limits']==LIMITS,'retention policy changed')
    selected=freeze['retained_delta_inputs']
    require(type(selected) is list and selected==sorted(set(selected)) and len(selected)+1<=LIMITS['maximum_files'],
            'bounded exact delta snapshot selection required')
    require(set(selected)<=set(freeze['files']) and str(HERE/'inputs.json') not in selected,
            'delta selection escapes frozen sources')
    rows={name:freeze['files'][name] for name in selected}
    rows[str(HERE/'inputs.json')]=file(HERE/'inputs.json')
    require(all(row['size']<=LIMITS['maximum_file_bytes'] for row in rows.values())
            and sum(row['size'] for row in rows.values())<=LIMITS['maximum_logical_bytes'],
            'compact delta proof size exceeds unchanged explicit limits')
    unique_sizes={}
    for row in rows.values():
        require(row['sha256'] not in unique_sizes or unique_sizes[row['sha256']]==row['size'],
                'equal-hash proof sizes differ')
        unique_sizes[row['sha256']]=row['size']
    allocated=sum((size+4095)//4096*4096 for size in unique_sizes.values())
    return dict(files=rows,unique_files=len(unique_sizes),logical_bytes=sum(r['size'] for r in rows.values()),
        projected_allocated_bytes=allocated,
        projected_reservation_bytes=allocated+LIMITS['metadata_reservation_bytes']+LIMITS['remaining_evidence_reservation_bytes'])


class Reconciliation:
    def __init__(self,expected):
        require(Path.cwd()==A and sys.dont_write_bytecode and not sys.flags.optimize,
                'fixed owner and unoptimized Python -B required')
        require(file(HERE/'inputs.json')['sha256']==expected,'reviewed reconciliation freeze required')
        self.inputs_sha256=expected;self.freeze=read(HERE/'inputs.json')
        self.base,self.inputs=merged_inputs(self.freeze)
        self.plan=read(HERE/'plan.json')
        require(file(HERE/'plan.json')['sha256']==self.freeze['plan_sha256'],'reconciliation plan differs')
        self.owned=module('owned_stage',OWNED,self.inputs['files'])
        self.monitor=module('reconciliation_monitor',MONITOR,self.inputs['files'])
        self.projection=retention_projection(self.freeze)
        self.started=time.monotonic();self.last_sample=0;self.active=False
        self.record=dict(status='starting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),
            identity=dict(source='in-process observation',pid=os.getpid(),parent_pid=os.getppid(),
                          pgid=os.getpgrp(),cwd=os.getcwd(),argv=sys.argv),
            inputs_sha256=expected,plan_sha256=self.freeze['plan_sha256'],commands=[],
            read_only_reconciliation=True,actual_workload_children=0,saved_actual_children=20,historical_failed_children=11,
            command_evidence=self.plan['command_evidence'],reconciliation=self.plan['reconciliation'],
            native_roles_and_behavior_qualified=False,hash_driver_qualified=False,application_qualified=False,
            runtime_installation=False,benchmark=False,samples=[])

    def write(self,path,value):
        data=encoded(value);require(len(data)<=LIMITS['maximum_document_bytes'],'bounded reconciliation document required')
        path=Path(path);staged=path.with_name(path.name+'.staged')
        require(not staged.exists() and not staged.is_symlink(),'unexpected staged publication')
        with staged.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        staged.replace(path)
        require(file(path)['sha256']==hashlib.sha256(data).hexdigest(),'published document readback differs')

    def save(self):self.write(WORK/'receipt.json',self.record)

    def budget(self):
        row=self.monitor.sample(evidence_root=WORK,evidence_roots=list(map(Path,self.plan['reconciliation_evidence_roots'])))
        require(self.monitor.rejection(row) is None,'reconciliation aggregate capacity rejected')
        return row

    def guard(self):
        require(shutil.disk_usage(A).free>=9*2**30,'free space below9GiB during read-only reconciliation')
        require(time.monotonic()-self.started<=600,'bounded reconciliation read deadline exceeded')
        if time.monotonic()-self.last_sample>=5:
            self.record['samples'].append(self.budget());self.last_sample=time.monotonic()
            if self.active:self.save()

    def check(self,path):
        path=Path(path);file(path,self.inputs['files'][str(path)],self.guard);return path

    def full_guard(self):
        verify_inputs(self.inputs,self.guard)
        for name,resolved in self.freeze['routes'].items():
            require(str(Path(name).resolve(strict=True))==resolved,'new proof executor/source route differs')
        for root,expected in self.freeze['memberships'].items():
            current={str(p.relative_to(root)):'directory' if p.is_dir() else 'file'
                for p in Path(root).rglob('*') if not p.is_symlink()}
            require(current==expected and not any(p.is_symlink() for p in Path(root).rglob('*')),
                    'closed evidence membership differs')

    def retain(self):
        destination=WORK/'delta-proof';destination.mkdir();physical={}
        for name,row in self.projection['files'].items():
            self.guard();file(name,row,self.guard);key=row['sha256']
            if key not in physical:
                path=destination/key
                with os.fdopen(os.open(name,os.O_RDONLY|os.O_NOFOLLOW),'rb') as source,path.open('xb') as output:
                    require({key:getattr(os.fstat(source.fileno()),'st_'+key) for key in FIELDS}==row['identity'],
                            'held delta input changed')
                    total=0
                    while block:=source.read(min(2**20,row['size']-total+1)):
                        self.guard();total+=len(block)
                        require(total<=row['size'],'delta copy exceeded exact frozen length')
                        output.write(block)
                    require(total==row['size'] and identity(name)==row['identity']
                        and {key:getattr(os.fstat(source.fileno()),'st_'+key) for key in FIELDS}==row['identity'],
                        'delta input changed during retained copy')
                    output.flush();os.fsync(output.fileno())
                current=file(path,guard=self.guard)
                require(current['sha256']==key and current['size']==row['size'] and current['identity']['nlink']==1,
                        'delta proof copy differs')
                physical[key]=dict(path=str(path),**current)
        require(set(path.name for path in destination.iterdir())==set(physical),'delta physical membership differs')
        manifest=dict(files={name:dict(path=physical[row['sha256']]['path'],sha256=row['sha256'],size=row['size'])
                             for name,row in self.projection['files'].items()},physical=physical,
            base_inputs=self.freeze['base_inputs'],original_snapshots=dict(source=str(ORIGINAL_SOURCE),evidence=str(ORIGINAL_WORK)),
            full_readback=True,logical_bytes=self.projection['logical_bytes'])
        self.write(WORK/'delta-proof.json',manifest);self.record['delta_proof_sha256']=file(WORK/'delta-proof.json')['sha256']

    def reconcile(self):
        original=read(ORIGINAL_SOURCE/'plan.json')
        require(set(self.plan)==set(original)|ADDITIONS
                and encoded({key:self.plan[key] for key in original})==encoded(original)
                and self.plan['read_only_reconciliation'] is True
                and type(self.plan['actual_workload_children']) is int and self.plan['actual_workload_children']==0,
                'historical native plan was changed')
        require(self.plan['reconciliation_evidence_roots']==sorted(set(original['evidence_roots'])|{str(WORK)}),
                'new evidence root omitted from aggregate')
        controls=module('reconciliation_parser_controls',HERE/'parser_controls.py',self.inputs['files'])
        proof=controls.validate(self.check,self.inputs['files'])
        require(proof==self.plan['reconciliation']['parser_controls'],'actual parser qualification differs')
        failure_audit(self.check)
        reader=module('reconciliation_readback',HERE/'readback.py',self.inputs['files'])
        readback,context=reader.readback(self.guard)
        receipt=context['receipt'];paths=context['paths'];rows=context['rows']
        required,reconciliation=provenance(original,receipt,proof,self.inputs['files'])
        require(self.plan['command_evidence']==required and self.plan['reconciliation']==reconciliation
                and self.plan['base_inputs']==self.freeze['base_inputs']==reconciliation['base_inputs'],
                'complete original command/reconciliation association differs')
        library,providers=beta_providers(original,self.inputs['files'])
        require(self.plan['wrong_beta_lib']==library and self.plan['wrong_beta_providers']==providers,
                'complete original B3 provider selection differs')
        parser=module('reconciliation_wrong_beta',HERE/'wrong_beta.py',self.inputs['files'])
        def provider(row):
            value=dict(path=row['path'],**file(row['path'],self.inputs['files'][row['path']],self.guard))
            require(value==row,'named provider differs from admitted B3 bytes');return value
        wrong=parser.wrong_pair((rows[18]['stdout'],rows[18]['stderr']),(rows[19]['stdout'],rows[19]['stderr']),
            observed=context['observed'],beta_lib=self.plan['wrong_beta_lib'],beta_std_paths=original['beta_std_paths'],
            providers=self.plan['wrong_beta_providers'],beta_version=original['build_version'].splitlines()[0],
            native_version=original['runtime_version'].splitlines()[0],verify_provider=provider)
        self.write(WORK/'original-readback.json',readback)
        result=dict(status='native-roles-and-behavior-qualified',candidate_revision=original['candidate_revision'],
            source_identity=original['source_identity'],assembly=original['assembly'],compiler=original['compiler'],
            stock=receipt['stock'],stock_source=receipt['stock_source'],stock_source_derivation=original['stock_source_derivation'],
            prior_failed_attempts=original['prior_failed_attempts'],loader_route_controls=original['loader_route_controls'],
            total_actual_native_children=31,qualified_native_children=20,
            ordered_driver_destinations=original['ordered_driver_destinations'],static_loader=receipt['static_loader'],
            actual_loader=receipt['actual_loader'],runtime_closure=original['runtime_closure'],source_restored=True,
            history=receipt['commands'][:18],wrong_B3_commands=receipt['commands'][18:],uncalled_error=receipt['uncalled_error'],
            wrong_B3=wrong,hits=receipt['hits'],native_executions=receipt['native_executions'],
            hash_driver_qualified=False,run_make_qualified=False,application_qualified=False,
            command_evidence=required,reconciliation=self.plan['reconciliation'])
        return result

    def execute(self):
        require(not WORK.exists() and not WORK.is_symlink(),'fresh reconciliation namespace required')
        with self.owned.workload_lock(self.owned.CANONICAL_LOCK,600):
            self.owned.disk(A,16);current=self.budget()
            require(current['evidence_allocated_bytes']+self.projection['projected_reservation_bytes']<=256*2**20,
                    'compact delta and unchanged remaining reserve exceed aggregate cap')
            WORK.mkdir();self.active=True
            self.record.update(status='running',admitted_at=time.time(),free_bytes_before=shutil.disk_usage(A).free,
                retention_admission=dict(existing_evidence_bytes=current['evidence_allocated_bytes'],
                    projected_reservation_bytes=self.projection['projected_reservation_bytes'],evidence_cap_bytes=256*2**20))
            self.save()
            try:
                self.full_guard();self.retain();result=self.reconcile();self.full_guard();self.guard()
                self.write(WORK/'native-controls.json',result);self.record['samples'].append(self.budget())
                self.record.update(status='passed',native_roles_and_behavior_qualified=True,
                    result_sha256=file(WORK/'native-controls.json')['sha256'],free_bytes_after=shutil.disk_usage(A).free)
            except BaseException as error:
                self.record.update(status='failed',error=repr(error));raise
            finally:
                self.record['finished_at']=time.time();self.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    Reconciliation(parser.parse_args().inputs_sha256).execute()

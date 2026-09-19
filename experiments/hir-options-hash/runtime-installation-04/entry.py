"""Concrete entry wiring; actual completed audits and a reviewed freeze required.

No work runs at import. The two phases retain separate evidence and exact child
recipes through the existing controller. Snapshot copies use the already
qualified bounded helper under the controller's canonical admission.
"""
import argparse
import ast
import copy
import importlib.util
import os
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
HASH_SOURCE=ROOT/'experiments/hir-options-hash-driver-stage-03'
FILE_TABLE_SOURCE=ROOT/'experiments/frozen-file-table-delta-01/file_table.py'
FILE_TABLE_BASE=dict(path='/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/experiments/hir-options-hash-native-controls-03/inputs.json',
    sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
CATALOG_SOURCE=ROOT/'experiments/completed-proof-snapshot-catalog-02/catalog.py'
CATALOG_TEST=CATALOG_SOURCE.with_name('test_catalog.py')
CATALOG_CONTROLS=ROOT/'experiments/hash-continuation-controls-01'
CATALOG_WORK=ROOT/'.work/hash-continuation-controls-01'
CATALOG_AUDIT=ROOT/'.work/hash-continuation-controls-independent-verification-01.json'
RUNTIME_CONTROLS=ROOT/'experiments/runtime-prerequisite-controls-04'
RUNTIME_CONTROL_WORK=ROOT/'.work/runtime-prerequisite-controls-04'
RUNTIME_CONTROL_AUDIT=ROOT/'.work/runtime-prerequisite-controls-independent-verification-04.json'
LIMITS=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
            maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
REMAINING_RESERVATION=32*2**20
RUNTIME_CONTROL_COUNT=52  # 37 Reader/factory plus 15 copy/collector/admission fixtures; actual proof still required.
RETIREMENT_AUDIT=ROOT/'.work/retained-proof-copy-retirement-independent-verification-01.json'


def require(ok,message):
    if not ok:raise RuntimeError(message)


def definition(name,path):
    spec=importlib.util.spec_from_file_location('_runtime_entry_04_'+name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[spec.name]=value;spec.loader.exec_module(value)
    return value


def records(freeze,packet,inputs_sha256,frozen):
    names=freeze['snapshot_inputs']
    require(names==sorted(set(names)) and set(names)<=set(freeze['files']),'snapshot selection differs')
    rows=[dict(path=name,**freeze['files'][name]) for name in names]
    p=packet/'inputs.json'
    rows.append(dict(path=str(p),sha256=inputs_sha256,size=p.stat().st_size,identity=frozen.identity(p)))
    return rows


def reservation(projection,rows,catalog):
    require(set(projection['files'])=={r['path'] for r in rows},'reservation omitted logical input')
    return catalog.reservation(projection,LIMITS['maximum_manifest_bytes'],REMAINING_RESERVATION)


def load_table(wire,f):
    require(wire.get('file_table_base')==FILE_TABLE_BASE,'exact nonrecursive runtime base required')
    row=wire['files'][str(FILE_TABLE_SOURCE)]
    require(f.identity(FILE_TABLE_SOURCE)==row['identity'] and f.digest(FILE_TABLE_SOURCE)==row['sha256']
        and FILE_TABLE_SOURCE.stat().st_size==row['size'],'file-table helper changed before import')
    return definition('file_table',FILE_TABLE_SOURCE)


def discovery(modules):
    """Separate historical copy rows without changing any ordinary read API."""
    class RuntimeDiscovery(modules.collector.Discovery):
        def __init__(self, hash_modules):
            super().__init__(hash_modules)
            self.historical_names=set()
            self.hash_original=None

        def add(self,path,expected=None,*,snapshot=False):
            require(str(path) not in self.historical_names,'historical proof copy has no current-file API')
            return super().add(path,expected,snapshot=snapshot)

        def inherit(self,source):
            source=Path(source)
            if source==HASH_SOURCE:
                require(self.hash_original is None,'completed hash inheritance may occur only once')
                wire=modules.collector.read(self.add(source/'inputs.json',snapshot=True))
                require(modules.collector.sha(source/'inputs.json')==modules.copies.ORIGINAL_INPUTS_SHA256,
                    'exact completed historical hash table required')
                self.add(FILE_TABLE_BASE['path'],FILE_TABLE_BASE,snapshot=True)
                table=modules.stage.load_file_table(wire,self.comp)
                full=modules.stage.expand_file_table(wire,table,guard=self.floor)
                names=modules.copies.selection(full,
                    read_json=lambda p:modules.collector.read(self.add(p,snapshot=True)),
                    sha=lambda p:modules.collector.sha(self.add(p,snapshot=True)))
                require(not set(names)&set(self.files),'historical copy was already admitted as current')
                self.historical_names=set(names)
                plan_wire=modules.collector.read(self.add(source/'plan.json',snapshot=True))
                require(modules.collector.sha(source/'plan.json')==full['plan_sha256'],'completed raw plan changed')
                self.add(modules.stage.PLAN_REFERENCE_SOURCE,full['files'][str(modules.stage.PLAN_REFERENCE_SOURCE)],snapshot=True)
                helper=modules.stage.load_plan_reference(full,self.comp)
                plan=modules.stage.expand_plan(plan_wire,helper,lambda p:self.add(p).read_bytes())
                for name,row in full['files'].items():
                    if name not in self.historical_names:self.add(name,row)
                for name,row in full['links'].items():self.link(name,row)
                for name in full['absent_paths']:
                    require(not Path(name).exists() and not Path(name).is_symlink(),'hash predecessor absence changed')
                    self.absent.add(name)
                self.hash_original=copy.deepcopy(full)
                return plan
            if source!=HERE/'preflight-plan-01':return super().inherit(source)
            wire=modules.collector.read(self.add(source/'inputs.json',snapshot=True))
            self.add(FILE_TABLE_BASE['path'],FILE_TABLE_BASE,snapshot=True)
            table=modules.stage.load_file_table(wire,self.comp)
            full=modules.stage.expand_file_table(wire,table,guard=self.floor)
            plan=modules.collector.read(self.add(source/'plan.json',snapshot=True))
            require(plan['hash_source']==str(HASH_SOURCE) and plan['phase']=='preflight'
                and modules.collector.sha(source/'plan.json')==full['plan_sha256'],'exact prior runtime preflight packet required')
            for name,row in full['files'].items():self.add(name,row)
            for name,row in full['links'].items():self.link(name,row)
            for name in full['absent_paths']:
                require(not Path(name).exists() and not Path(name).is_symlink(),'runtime predecessor absence changed')
                self.absent.add(name)
            return plan
    return RuntimeDiscovery(modules.hash_modules)


def copy_partition(modules,reader,*,load,directory_record,saved=None):
    """Authenticate actual40 and every predecessor witness before Reader.check."""
    s=reader.reader;c=modules.copies
    proof=controls_qualification(reader,source=c.SOURCE/'references.py',test=c.SOURCE/'test_references.py',
        controls=c.CONTROLS,work=c.CONTROL_WORK,audit_path=c.CONTROL_AUDIT,count=40)
    require(proof['audit']==dict(path=str(c.CONTROL_AUDIT),sha256=c.CONTROL_AUDIT_SHA256),
        'exact qualified copy helper audit required')
    references=load('copy_references',c.SOURCE/'references.py',s.frozen)
    # Reader has authenticated actual22 before reaching this callback.
    snapshots=load('qualified_snapshots',modules.stage.SNAPSHOT_SOURCE,s.frozen)
    def absent(path):
        require(str(path) in s.freeze['absent_paths'] and not Path(path).exists()
            and not Path(path).is_symlink(),'frozen predecessor absence changed')
        return True
    return c.bootstrap(modules.stage,modules.hash_modules,reader.original,reader.plan,s.freeze['files'],
        reader.plan['evidence_roots'],references,snapshots,helper_qualification=proof,
        read_json=s.read_json,read_bytes=s.read_bytes,sha=lambda p:s.owned.sha(s.frozen(p)),
        file_record=lambda p:dict(path=str(s.frozen(p)),**s.freeze['files'][str(p)]),
        directory_record=directory_record,check_absent=absent,guard=lambda:s.owned.disk(ROOT,9),saved=saved)


def retirement_qualification(modules,reference,state,*,read_json,sha):
    """Production admission requires a separate actual post-retirement audit.

    The pre-retirement strict-reader rehearsal never calls this gate and never
    creates a runtime packet or WORK. All names must actually be absent here.
    """
    c=modules.copies
    require(type(reference) is dict and set(reference)=={'path','sha256'}
        and reference['path']==str(RETIREMENT_AUDIT)
        and type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}',reference['sha256'])
        and sha(RETIREMENT_AUDIT)==reference['sha256'],'exact actual copy-retirement audit required')
    audit=read_json(RETIREMENT_AUDIT)
    require(audit['status']=='verified-exact-proof-copy-retirement'
        and audit['proposal_sha256']==c.PROPOSAL_SHA256
        and audit['historical_source_stage03_wire_sha256']==c.ORIGINAL_INPUTS_SHA256
        and audit['helper40_audit']==dict(path=str(c.CONTROL_AUDIT),sha256=c.CONTROL_AUDIT_SHA256)
        and audit['original_retained_inputs_sha256']=='587139f94eeb3d6ccac398f9c12ec65f4eb33b0e79b40e513678826cdd9f2c0d'
        and audit['selected_paths']==sorted(state['historical_files'])
        and all(type(audit[k]) is int and audit[k]==v for k,v in
            dict(removed_files=21,preserved_files=40,removed_directories=0,chmod_operations=0,
                 durable_events=63,current_context_rows=109322).items())
        and all(audit[k] is True for k in ['full_ledger_replay','source_witness_readback','preserved40_readback']),
        'actual exact-copy retirement proof differs')
    for key in ['recovery','runtime_rehearsal']:
        ref=audit[key]
        require(set(ref)=={'path','sha256'} and sha(ref['path'])==ref['sha256'],
            'retirement recovery or rehearsal report changed')
    rehearsal=read_json(audit['runtime_rehearsal']['path'])
    require(rehearsal['status']=='verified-strict-callback-rehearsal'
        and rehearsal['proposal_sha256']==c.PROPOSAL_SHA256
        and rehearsal['historical_source_stage03_wire_sha256']==c.ORIGINAL_INPUTS_SHA256
        and all(type(rehearsal[k]) is int and rehearsal[k]==v for k,v in
            dict(complete_original_rows=109343,current_context_rows=109322,historical_copies=21).items())
        and rehearsal['bootstrap_policy']=='continued-catalog-before-reader'
        and rehearsal['no_live_api_virtualization'] is True
        and rehearsal['runtime_admission'] is False and rehearsal['retirement_authorized'] is False,
        'separate current-reader rehearsal required')
    for name in state['historical_files']:
        require(not Path(name).exists() and not Path(name).is_symlink(),'retired copy is still present')
    return copy.deepcopy(reference)


def controls_qualification(reader,*,source,test,controls,work,audit_path,count,additional_sources=(),additional_tests=()):
    """Require actual bounded controls before importing the new pure catalog."""
    CATALOG_SOURCE,CATALOG_TEST,CATALOG_CONTROLS,CATALOG_WORK,CATALOG_AUDIT=source,test,controls,work,audit_path
    s=reader.reader
    for p in [CATALOG_SOURCE,CATALOG_TEST,CATALOG_CONTROLS/'inputs.json',CATALOG_CONTROLS/'launch.json',
              CATALOG_WORK/'receipt.json',CATALOG_WORK/'result.json',CATALOG_WORK/'command/receipt.json',
              CATALOG_WORK/'command/stdout',CATALOG_WORK/'command/stderr',CATALOG_AUDIT]:s.frozen(p)
    inputs=s.read_json(CATALOG_CONTROLS/'inputs.json');launch=s.read_json(CATALOG_CONTROLS/'launch.json')
    require(all(str(p) in inputs['files'] for p in [source,test,*additional_tests,*additional_sources]),
        'actual controls omitted selected source/helper')
    for name,row in inputs['files'].items():
        s.frozen(name);current=s.freeze['files'][name]
        require(current['sha256']==row['sha256'] and [current['identity'][k] for k in
            ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]==row['stamp'],'catalog control frozen source changed')
    for name,target in inputs['routes'].items():require(str(Path(name).resolve(strict=True))==target,'catalog control route changed')
    names=[]
    for test_path in [test,*additional_tests]:
        tree=ast.parse(s.read_bytes(test_path));names.extend(test_path.stem+'.'+c.name+'.'+m.name for c in tree.body
            if isinstance(c,ast.ClassDef) for m in c.body if isinstance(m,ast.FunctionDef) and m.name.startswith('test_'))
    names=sorted(names)
    terminal=s.read_json(CATALOG_WORK/'receipt.json');result=s.read_json(CATALOG_WORK/'result.json')
    child=s.read_json(CATALOG_WORK/'command/receipt.json');audit=s.read_json(CATALOG_AUDIT)
    require(len(names)==count and inputs['expected_names']==result['expected_names']==names
        and terminal['status']==result['status']=='passed' and terminal['controls_passed']==result['tests_run']==len(names)
        and audit['status']=='verified' and audit['controls']==len(names) and sorted(audit['exact_names'])==names
        and audit['receipt_sha256']==s.owned.sha(CATALOG_WORK/'receipt.json')
        and terminal['result_sha256']==audit['result_sha256']==s.owned.sha(CATALOG_WORK/'result.json')
        and terminal['inputs_sha256']==launch['inputs_sha256']==s.owned.sha(CATALOG_CONTROLS/'inputs.json'),
        'actual completed catalog controls required')
    require(all(result[k]==0 and type(result[k]) is int for k in
        ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls'])
        and all(terminal[k]==0 for k in ['compiler_calls','provider_probes','B3_compositions']), 'catalog controls did unexpected work')
    require(child['status']=='finished' and child['returncode']==0 and child['command']==inputs['command']
        and child['cwd']==str(CATALOG_SOURCE.parent) and child['environment']==inputs['environment']
        and child['supervisor_pid']==terminal['pid'] and child['parent_pid']==terminal['parent_pid']
        and terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']
        and terminal['commands']==[dict(path=str(CATALOG_WORK/'command/receipt.json'),pid=child['pid'],
            sha256=s.owned.sha(CATALOG_WORK/'command/receipt.json'))],'catalog actual child association differs')
    for stream in ['stdout','stderr']:
        require(child[stream+'_sha256']==audit['raw_sha256'][stream]==s.owned.sha(CATALOG_WORK/'command'/stream),'catalog raw hash changed')
    raw=s.read_bytes(CATALOG_WORK/'command/stderr').decode()
    actual=re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$',raw,re.M)
    require(sorted(actual)==names and len(actual)==len(names) and not s.read_bytes(CATALOG_WORK/'command/stdout')
        and re.search(r'^Ran '+str(len(names))+r' tests in [0-9.]+s\n\nOK\n$',raw,re.M),'catalog exact actual controls differ')
    return dict(controls=len(names),source=str(CATALOG_CONTROLS),evidence=str(CATALOG_WORK),
        receipt_sha256=s.owned.sha(CATALOG_WORK/'receipt.json'),result_sha256=s.owned.sha(CATALOG_WORK/'result.json'),
        audit=dict(path=str(CATALOG_AUDIT),sha256=s.owned.sha(CATALOG_AUDIT)))


def catalog_qualification(reader):
    s=reader.reader
    return reader.stage.continuation_qualification(read_json=s.read_json,read_bytes=s.read_bytes,
        sha=lambda p:s.owned.sha(s.frozen(p)),
        file_record=lambda p:dict(path=str(s.frozen(p)),**s.freeze['files'][str(p)]))


def runtime_qualification(reader):
    return controls_qualification(reader,source=HERE/'prerequisites.py',test=HERE/'test_prerequisite_successor.py',
        controls=RUNTIME_CONTROLS,work=RUNTIME_CONTROL_WORK,audit_path=RUNTIME_CONTROL_AUDIT,count=RUNTIME_CONTROL_COUNT,
        additional_sources=(HERE/'imports.py',HERE/'copies.py',HERE/'entry.py'),
        additional_tests=(HERE/'test_copy_references.py',))


def completed_catalog(modules,reader,catalog,snapshots,roots,*,read_json,read_bytes,sha,file_record,directory_record,guard,preflight_owner=None):
    def check_absent(path):
        require(str(path) in reader.reader.freeze['absent_paths']
            and not Path(path).exists() and not Path(path).is_symlink(),'frozen failed-owner output absence changed')
        return True
    prior=modules.stage.continued_catalog(modules.hash_modules,reader.reader.freeze,modules.hash_modules['comp'],
        reader.plan['independent_audits'],roots,snapshots,read_json=read_json,read_bytes=read_bytes,sha=sha,
        file_record=file_record,directory_record=directory_record,check_absent=check_absent,guard=guard)
    require(catalog.encoded(prior)==catalog.encoded(reader.copy_state['prior_catalog']),
        'completed catalog differs from authenticated copy bootstrap')
    def catalog_json(path):
        # The generic catalog authenticates raw file_record bytes independently.
        # Only this exact completed owner has an external-member plan envelope.
        if Path(path)==HASH_SOURCE/'plan.json':
            file_record(path)
            return reader.read_hash_plan()
        return read_json(path)
    def expand(wire,row):
        if 'file_table_base' not in wire:return wire
        require(wire['file_table_base']==FILE_TABLE_BASE,'unreviewed completed snapshot base')
        table=modules.stage.load_file_table(wire,modules.hash_modules['comp'])
        return modules.stage.expand_file_table(wire,table,guard=guard)
    owner=dict(role='hash',source=str(HASH_SOURCE),evidence=str(modules.stage.WORK),audit=reader.references['hash'],
        result_path=str(modules.stage.WORK/'result.json'),result_digest_field='result_sha256')
    result=catalog.extend(prior,owner,roots,LIMITS,read_json=catalog_json,file_record=file_record,
        directory_record=directory_record,expand_inputs=expand,validate_owner=reader.snapshot_owner)
    if preflight_owner is not None:
        owner,validate=preflight_owner
        result=catalog.extend(result,owner,roots,LIMITS,read_json=catalog_json,file_record=file_record,
            directory_record=directory_record,expand_inputs=expand,validate_owner=validate)
    # Qualified v2 performs full compressed/logical EOF for EVERY catalog row,
    # including rows not selected for this stage. This does not create copies.
    for row in result['records']:snapshots.verify_reference(row,result['evidence_roots'],guard)
    actual={row['path']:row for row in result['records']}
    require(all(row['path'] in actual and catalog.encoded(actual[row['path']])==catalog.encoded(row)
        for row in reader.copy_state['references']['witnesses'].values()), 'completed catalog omitted a historical-copy witness')
    return result


def preflight_catalog_owner(modules,plan,*,read_json,read_bytes,sha):
    if plan['phase']!='installation':return None
    previous=HERE/'preflight-plan-01';work=R/'.work/hir-options-hash-runtime-preflight-04'
    previous_plan=read_json(previous/'plan.json');candidate=read_json(previous_plan['specification']['path'])
    history=modules.preflight_history.validate(modules.q,modules.recipe,packet=previous,work=work,candidate=candidate,
        audit_reference=plan['source_preflight_readback']['audit'],read_json=read_json,read_bytes=read_bytes,sha=sha)
    encoded=modules.hash_modules['snapshot_bindings'].encoded
    same=lambda left,right:encoded(left)==encoded(right)
    require(same(history,plan['source_preflight_readback']),'actual completed source-preflight qualification changed')
    owner=dict(role='source_preflight',source=str(previous),evidence=str(work),audit=history['audit'],
        result_path=str(work/'source-probe/result.json'),result_digest_field='source_preflight_sha256')
    def validate(given,terminal,result,audit):
        # history.validate above performs the full two-probe/recipe proof once;
        # this callback only binds those authenticated objects, never recurses.
        require(same(given,owner) and same(terminal,read_json(work/'receipt.json')) and same(result,history['result'])
            and sha(work/'receipt.json')==history['receipt_sha256']
            and sha(work/'source-probe/result.json')==history['reference']['sha256']
            and same(audit,read_json(owner['audit']['path'])) and sha(owner['audit']['path'])==owner['audit']['sha256'],
            'completed preflight snapshot owner differs')
        return True
    return owner,validate


def execute(packet,inputs_sha256,snapshot_sha256):
    require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'fixed R owner/Python flags required')
    require(packet.parent==HERE and packet.name in ['preflight-plan-01','installation-plan-01'],'exact reviewed packet namespace required')
    f=definition('frozen',HERE/'frozen.py')
    require(f.digest(packet/'inputs.json')==inputs_sha256,'exact union freeze required')
    wire=f.json_file(packet/'inputs.json');plan=f.json_file(packet/'plan.json')
    require(f.digest(packet/'plan.json')==wire['plan_sha256'] and plan['hash_source']==str(HASH_SOURCE),'actual plan/source binding differs')
    require(plan['phase']==('preflight' if packet.name=='preflight-plan-01' else 'installation'),'phase packet differs')
    table=load_table(wire,f)
    bound=f.Frozen(packet/'inputs.json',inputs_sha256,output_root=plan['work'],table=table,base=FILE_TABLE_BASE);bound.check(True)
    raw=bound.value
    require(str(Path(sys.executable).resolve(strict=True))==raw['python'],'actual Python route differs')
    for path in [Path(__file__).resolve(),HERE/'frozen.py',HERE/'imports.py']:bound.file(path)
    factory=definition('imports',HERE/'imports.py')
    modules=factory.definitions(HASH_SOURCE,bound.file)
    reader=modules.prerequisites.Reader(modules.stage,modules.hash_modules,combined_freeze=raw,
        references=plan['independent_audits'],read_json=bound.read_json,sha=bound.sha,
        copy_partition=lambda r:copy_partition(modules,r,load=factory.load,directory_record=f.ordinary_directory,
            saved=raw['historical_copies']))
    require(raw['historical_copies']==reader.copy_state['references'],'runtime historical reference table differs')
    retirement_qualification(modules,plan['copy_retirement'],reader.copy_state,read_json=bound.read_json,sha=bound.sha)
    qualified=reader.check(full=True)
    require(qualified==plan['qualified_prerequisites'],'actual qualification summary differs')
    # Pure helper qualification reads the actual passed control history, with
    # every inherited proof in the complete combined freeze.
    reader.reader.snapshot_qualification()
    require(runtime_qualification(reader)==plan['runtime_adapter_qualification'],'actual runtime adapter qualification differs')
    require(catalog_qualification(reader)==plan['catalog_qualification'],'actual catalog qualification differs')
    catalog=factory.load('completed_catalog',CATALOG_SOURCE,bound.file)
    snap_path=packet/'snapshot-plan.json'
    require(f.digest(snap_path)==snapshot_sha256,'exact reviewed runtime snapshot projection required')
    snapshot=f.json_file(snap_path);helper=modules.stage.SNAPSHOT_SOURCE
    bound.file(helper)
    require(snapshot['inputs_sha256']==inputs_sha256 and snapshot['helper']==dict(path=str(helper),sha256=bound.sha(helper))
        and snapshot['limits']==LIMITS and snapshot['remaining_evidence_reservation_bytes']==REMAINING_RESERVATION
        and snapshot['evidence_cap_bytes']==256*2**20,'runtime snapshot policy differs')
    rows=records(raw,packet,inputs_sha256,f)
    helper_module=factory.load('qualified_snapshots',helper,bound.file)
    state={}
    def check(full=False):
        bound.check(full)
        retirement_qualification(modules,plan['copy_retirement'],reader.copy_state,read_json=bound.read_json,sha=bound.sha)
        require(f.digest(snap_path)==snapshot_sha256,'reviewed snapshot projection changed')
        controller=state.get('controller')
        if full and controller is not None and controller.record['status']=='running' and 'source_snapshots_sha256' not in controller.record:
            require(reader.check(full=True)==plan['qualified_prerequisites'],'full completed owner qualification changed')
            lineage=completed_catalog(modules,reader,catalog,helper_module,plan['evidence_roots'],
                read_json=bound.read_json,read_bytes=bound.read_bytes,sha=bound.sha,file_record=bound.record,
                directory_record=f.ordinary_directory,guard=controller.capacity,
                preflight_owner=preflight_catalog_owner(modules,plan,read_json=bound.read_json,read_bytes=bound.read_bytes,sha=bound.sha))
            require(catalog.encoded(lineage)==catalog.encoded(plan['snapshot_reuse']),'complete runtime ancestry changed')
            selected=catalog.select(rows,lineage)
            require(catalog.encoded(selected)==catalog.encoded(snapshot['reuse_selection']),'complete runtime reference selection changed')
            temporary=controller.work/'tmp'
            require(plan['environment']['TMPDIR']==str(temporary) and not temporary.exists() and not temporary.is_symlink(),'fresh owned temporary directory required')
            temporary.mkdir()
            projection=helper_module.measure(rows,LIMITS,controller.capacity,reuse=selected['records'],evidence_roots=selected['evidence_roots'])
            require(projection==snapshot['projection'],'actual source snapshot projection differs')
            budget=controller.capacity(force=True);amount=reservation(projection,rows,catalog)
            require(amount==snapshot['projected_reservation_bytes']
                and budget['evidence_allocated_bytes']+amount<=256*2**20,'aggregate evidence snapshot reservation unavailable')
            controller.record['snapshot_admission']=dict(existing_evidence_bytes=budget['evidence_allocated_bytes'],reserved_bytes=amount)
            controller.save()
            manifest=helper_module.write_verified(rows,controller.work/'source-snapshots',projection,LIMITS,controller.capacity,
                reuse=selected['records'],evidence_roots=selected['evidence_roots'])
            data=helper_module.encoded(manifest);require(len(data)<=LIMITS['maximum_manifest_bytes'],'snapshot manifest bound')
            with (controller.work/'source-snapshots.json').open('xb') as stream:
                stream.write(data);stream.flush();os.fsync(stream.fileno())
            with (controller.work/'snapshot-plan.json').open('xb') as stream:
                source=dict(path=str(snap_path),sha256=snapshot_sha256,size=snap_path.stat().st_size,identity=f.identity(snap_path))
                modules.hash_modules['comp'].check_file(source,stream,controller.capacity)
            require(f.digest(controller.work/'snapshot-plan.json')==snapshot_sha256,'retained projection differs')
            controller.record.update(snapshot_plan_sha256=snapshot_sha256,source_snapshots_sha256=f.digest(controller.work/'source-snapshots.json'))
            controller.save();controller.capacity(force=True)
    with factory.aliases(modules.public_aliases):
        controller=modules.controller.Controller(plan=plan,inputs_sha256=inputs_sha256,q=modules.q,recipe=modules.recipe,
            reader=reader,monitor=modules.monitor,check_frozen=check,read_json=bound.read_json,read_bytes=bound.read_bytes,sha=bound.sha)
        state['controller']=controller
        controller.record.update(plan_sha256=f.digest(packet/'plan.json'),snapshot_plan_sha256=snapshot_sha256)
        controller.save();controller.execute()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--inputs-sha256',required=True);parser.add_argument('--snapshot-plan-sha256',required=True)
    args=parser.parse_args();execute(args.packet,args.inputs_sha256,args.snapshot_plan_sha256)

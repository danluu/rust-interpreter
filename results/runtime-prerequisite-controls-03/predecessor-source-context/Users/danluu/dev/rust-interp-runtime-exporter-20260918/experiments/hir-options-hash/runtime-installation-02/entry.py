"""Concrete entry wiring; actual completed audits and a reviewed freeze required.

No work runs at import. The two phases retain separate evidence and exact child
recipes through the existing controller. Snapshot copies use the already
qualified bounded helper under the controller's canonical admission.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HASH_SOURCE=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/hir-options-hash-driver-stage')
LIMITS=dict(maximum_files=1024,maximum_file_bytes=64*2**20,maximum_logical_bytes=512*2**20,
            maximum_compressed_bytes=128*2**20,maximum_manifest_bytes=4*2**20)
REMAINING_RESERVATION=32*2**20


def require(ok,message):
    if not ok:raise RuntimeError(message)


def definition(name,path):
    spec=importlib.util.spec_from_file_location('_runtime_entry_02_'+name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[spec.name]=value;spec.loader.exec_module(value)
    return value


def records(freeze,packet,inputs_sha256,frozen):
    names=freeze['snapshot_inputs']
    require(names==sorted(set(names)) and set(names)<=set(freeze['files']),'snapshot selection differs')
    rows=[dict(path=name,**freeze['files'][name]) for name in names]
    p=packet/'inputs.json'
    rows.append(dict(path=str(p),sha256=inputs_sha256,size=p.stat().st_size,identity=frozen.identity(p)))
    return rows


def reservation(projection,rows):
    return projection['compressed_bytes']+4096*len(rows)+2*LIMITS['maximum_manifest_bytes']+REMAINING_RESERVATION


def execute(packet,inputs_sha256,snapshot_sha256):
    require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'fixed R owner/Python flags required')
    require(packet.parent==HERE and packet.name in ['preflight-plan-01','installation-plan-01'],'exact reviewed packet namespace required')
    f=definition('frozen',HERE/'frozen.py')
    require(f.digest(packet/'inputs.json')==inputs_sha256,'exact union freeze required')
    raw=f.json_file(packet/'inputs.json');plan=f.json_file(packet/'plan.json')
    require(f.digest(packet/'plan.json')==raw['plan_sha256'] and plan['hash_source']==str(HASH_SOURCE),'actual plan/source binding differs')
    require(plan['phase']==('preflight' if packet.name=='preflight-plan-01' else 'installation'),'phase packet differs')
    bound=f.Frozen(packet/'inputs.json',inputs_sha256,output_root=plan['work']);bound.check(True)
    require(str(Path(sys.executable).resolve(strict=True))==raw['python'],'actual Python route differs')
    for path in [Path(__file__).resolve(),HERE/'frozen.py',HERE/'imports.py']:bound.file(path)
    factory=definition('imports',HERE/'imports.py')
    modules=factory.definitions(HASH_SOURCE,bound.file)
    reader=modules.prerequisites.Reader(modules.stage,modules.hash_modules,combined_freeze=raw,
        references=plan['independent_audits'],read_json=bound.read_json,sha=bound.sha)
    qualified=reader.check(full=True)
    require(qualified==plan['qualified_prerequisites'],'actual qualification summary differs')
    # Pure helper qualification reads the actual passed control history, with
    # every inherited proof in the complete combined freeze.
    reader.reader.snapshot_qualification()
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
        require(f.digest(snap_path)==snapshot_sha256,'reviewed snapshot projection changed')
        controller=state.get('controller')
        if full and controller is not None and controller.record['status']=='running' and 'source_snapshots_sha256' not in controller.record:
            temporary=controller.work/'tmp'
            require(plan['environment']['TMPDIR']==str(temporary) and not temporary.exists() and not temporary.is_symlink(),'fresh owned temporary directory required')
            temporary.mkdir()
            projection=helper_module.measure(rows,LIMITS,controller.capacity)
            require(projection==snapshot['projection'],'actual source snapshot projection differs')
            budget=controller.capacity(force=True);amount=reservation(projection,rows)
            require(amount==snapshot['projected_reservation_bytes']
                and budget['evidence_allocated_bytes']+amount<=256*2**20,'aggregate evidence snapshot reservation unavailable')
            controller.record['snapshot_admission']=dict(existing_evidence_bytes=budget['evidence_allocated_bytes'],reserved_bytes=amount)
            controller.save()
            manifest=helper_module.write_verified(rows,controller.work/'source-snapshots',projection,LIMITS,controller.capacity)
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

"""Pure saved-evidence readback; never imports workload controllers or providers."""
import gzip
import hashlib
import json
from pathlib import Path
import re

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE=A/'experiments/hir-options-hash-beta-composition-08'
WORK=A/'.work/hir-options-hash-beta-composition-08'
OUTER=A/'.work/experiments/hir-options-hash-beta-composition-supervisor-08'
LAUNCHER=A/'.work/beta-composition-launch-execution-08'
AUDIT=A/'.work/beta-composition-independent-verification-08.json'

def require(ok,message):
    if not ok: raise RuntimeError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):
    path=Path(path);require(path.stat().st_size<=64*2**20,'bounded saved JSON')
    return json.loads(path.read_bytes())

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()

def snapshots(terminal,disk):
    frozen=read(SOURCE/'inputs.json');plan=read(SOURCE/'snapshot-plan.json');projection=plan['projection']
    manifest=read(WORK/'source-snapshots.json')
    require(sha(WORK/'snapshot-plan.json')==sha(SOURCE/'snapshot-plan.json')==terminal['snapshot_plan_sha256']
        and sha(WORK/'source-snapshots.json')==terminal['source_snapshots_sha256'],'actual snapshot association')
    require(manifest['policy']==projection['policy']=='bounded-gzip-proof-snapshots-v1'
        and manifest['projection_sha256']==hashlib.sha256(encoded(projection)).hexdigest()
        and manifest['blobs']==projection['blobs']
        and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,'snapshot projection')
    names=set(frozen['snapshot_inputs'])|{str(SOURCE/'inputs.json')}
    require(names==set(projection['files'])==set(manifest['files']) and len(names)==287,'all logical snapshots')
    require(len(projection['blobs'])==220 and set(p.name for p in (WORK/'source-snapshots').iterdir())
        =={r['filename'] for r in projection['blobs'].values()},'all physical snapshots')
    for name,row in projection['files'].items():
        original=frozen['files'].get(name)
        if name==str(SOURCE/'inputs.json'):
            require(row['size']==(SOURCE/'inputs.json').stat().st_size and row['sha256']==sha(SOURCE/'inputs.json'),'own freeze snapshot')
        else:require(row==dict(path=name,**original),'snapshot original catalog mapping')
        require(manifest['files'][name]==dict(encoding='gzip',path=str(WORK/'source-snapshots'/(row['sha256']+'.gz')),
            sha256=row['sha256'],size=row['size']),'snapshot logical route')
    compressed=logical=0
    for digest,row in projection['blobs'].items():
        require(re.fullmatch('[a-f0-9]{64}',digest) and row['filename']==digest+'.gz'
            and row['logical_sha256']==digest and 0<=row['logical_bytes']<=64*2**20,'bounded snapshot blob')
        path=WORK/'source-snapshots'/row['filename'];before=path.stat()
        require(before.st_size==row['compressed_bytes'] and sha(path)==row['sha256'],'compressed snapshot identity')
        size=0;h=hashlib.sha256()
        with gzip.open(path,'rb') as stream:
            while block:=stream.read(min(2**20,row['logical_bytes']-size+1)):
                disk();size+=len(block);require(size<=row['logical_bytes'],'snapshot expansion bound');h.update(block)
        require(size==row['logical_bytes'] and h.hexdigest()==digest,'snapshot full logical/EOF hash')
        after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
            ==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'snapshot changed')
        compressed+=before.st_size;logical+=size
    require(compressed==projection['compressed_bytes']==manifest['compressed_bytes']==41567528,'compressed total')
    return dict(logical_files=287,physical_blobs=220,compressed_bytes=compressed,unique_logical_bytes=logical,full_gzip_eof_crc=True)

def validate_all(disk=lambda:None):
    terminal=read(WORK/'receipt.json');plan=read(SOURCE/'plan.json');launch=read(SOURCE/'launch.json')
    outer=read(OUTER/'status.json');launcher=read(LAUNCHER/'record.json');audit=read(AUDIT)
    require(terminal['status']=='passed' and terminal['assembly_and_auxiliary_strip_qualified'] is True
        and len(terminal['commands'])==len(plan['children'])==19,'actual passed B308')
    require(sha(WORK/'receipt.json')=='5d5fa5e6f7232c4079c39ad33e840d85a6dca5872374d4ac5de4312099ae6bbc'
        and sha(SOURCE/'inputs.json')==terminal['inputs_sha256']==launch['inputs_sha256'],'actual B308 fixed terminal/freeze')
    require(outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid']
        and outer['supervisor_pid']==terminal['parent_pid'] and outer['command']==launch['command'][6:]
        and outer['started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at'],'outer B308 association')
    require(launcher['status']=='finished' and launcher['returncode']==0 and launcher['command']==launch['command']
        and launcher['environment']==launch['environment'] and launcher['launch_sha256']==sha(SOURCE/'launch.json'),'explicit launcher wait')
    for stream in ['stdout','stderr']:require(sha(LAUNCHER/stream)==launcher[stream+'_sha256'],'launcher raw')
    require(audit['status']=='verified' and audit['receipt_sha256']==sha(WORK/'receipt.json')
        and audit['actual_children']==19 and audit['B3_files']==335
        and audit['output_inventory_sha256']==sha(WORK/'assembly/output-inventory.json')
        ==terminal['assembly']['output_inventory_sha256'],'independent actual audit')
    previous=terminal['admitted_at']
    for index,(reference,wanted) in enumerate(zip(terminal['commands'],plan['children'],strict=True)):
        path=WORK/'commands'/f'{index:03}'/'receipt.json';row=read(path)
        require(reference['path']==str(path) and reference['sha256']==sha(path) and reference['pid']==row['pid']
            and reference['command']==row['command']==wanted['argv'] and row['environment']==wanted['environment']
            and row['cwd']==wanted['cwd'] and row['status']=='finished' and row['returncode']==0
            and row['supervisor_pid']==terminal['pid'] and row['parent_pid']==terminal['parent_pid']
            and previous<=row['started_at']<=row['finished_at']<=terminal['finished_at'],'actual child association')
        for stream in ['stdout','stderr']:
            raw=path.parent/stream;require(raw.stat().st_size<=8*2**20 and sha(raw)==row[stream+'_sha256'],'actual raw stream')
        previous=row['finished_at']
    attempts=[]
    for suffix,source,code in [('', 'verify_beta_composition_08.py',1),('-sdk-route-01','verify_beta_composition_08_sdk_route_01.py',1),('-loader-projection-02','verify_beta_composition_08_loader_projection_02.py',0)]:
        prefix=A/('.work/beta-composition-independent-verification-execution-08'+suffix);record=read(str(prefix)+'.json')
        require(record['returncode']==code and record['command']==['/opt/homebrew/bin/python3','-B',str(A/'.work'/source)]
            and record['source_sha256']==sha(A/'.work'/source) and record['started_at']<=record['finished_at'],'retained verifier attempt')
        require(Path(str(prefix)+'.stdout').stat().st_size<=8*2**20 and Path(str(prefix)+'.stderr').stat().st_size<=8*2**20,'verifier raw bound')
        if code==0:require(audit['verifier_sha256']==record['source_sha256'] and audit['finished_at']<=record['finished_at'],'passed verifier identity')
        else:require(Path(str(prefix)+'.stderr').stat().st_size>0,'failure raw retained')
        attempts.append(dict(source=source,returncode=code,record_sha256=sha(str(prefix)+'.json')))
    rejected=read(A/'.work/beta-composition-prelaunch-rejection-07.json');source07=A/'experiments/hir-options-hash-beta-composition-07'
    require(rejected['status']=='unrun-prelaunch-capacity-rejection' and rejected['B3_compositions']==rejected['compiler_calls']==0,'unrun07 honest rejection')
    for name,key in [('inputs.json','freeze_sha256'),('plan.json','plan_sha256'),('launch.json','launch_sha256')]:
        require(sha(source07/name)==rejected[key],'original rejected07 proposal')
    q=ROOT/'.work/bounded-proof-snapshot-controls-01';qualified=read(q/'receipt.json');result=read(q/'result.json')
    qa=read(A/'.work/proof-snapshot-controls-independent-verification-01.json')
    require(qualified['status']==result['status']=='passed' and qa['status']=='verified'
        and qualified['controls_passed']==result['tests_run']==qa['controls']==7
        and qa['receipt_sha256']==sha(q/'receipt.json') and qa['result_sha256']==qualified['result_sha256']==sha(q/'result.json'),'seven helper qualification')
    require(all(result[k]==0 for k in ['errors','failures','skipped','unexpected_successes','expected_failures','child_processes','compiler_calls']),'helper control complete pass')
    child=read(q/'command/receipt.json');ref=qualified['commands'][0]
    require(len(qualified['commands'])==1 and ref['path']==str(q/'command/receipt.json') and ref['sha256']==sha(q/'command/receipt.json')
        and ref['pid']==child['pid'] and child['status']=='finished' and child['returncode']==0,'actual helper child')
    for stream in ['stdout','stderr']:require(sha(q/'command'/stream)==child[stream+'_sha256']==qa['raw_sha256'][stream],'helper raw proof')
    return dict(B3_actual_children=19,B3_files=335,receipt_sha256=sha(WORK/'receipt.json'),audit_sha256=sha(AUDIT),
        output_inventory_sha256=sha(WORK/'assembly/output-inventory.json'),snapshots=snapshots(terminal,disk),
        verifier_attempts=attempts,unavailable_contemporaneous_cwd=audit['unavailable_contemporaneous_cwd'],
        rejected07=rejected,helper_controls=7,helper_audit_sha256=sha(A/'.work/proof-snapshot-controls-independent-verification-01.json'),
        native_stock_qualified=False,hash_driver_qualified=False,application_qualified=False,performance_measurement=False)

"""Independent full native publication readback; unbound, source-only draft."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
import time
from types import ModuleType

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
D=ROOT/'experiments/native-qualification-publication-01'
W=ROOT/'.work/native-qualification-publication-01'
O=ROOT/'.work/experiments/native-qualification-publication-supervisor-01'
L=ROOT/'.work/native-qualification-publication-launch-execution-01'
RESULT=ROOT/'results/hir-options-hash-native-reconciliation-01'
SOURCES=ROOT/'experiments/native-qualification-source-01'
OUT=ROOT/'.work/native-qualification-publication-independent-verification-01.json'
EXPECTED_LAUNCH='794c436a08ca789dab8a13c65881281d34f2dc896d837a3368efc86db936005f'
EXPECTED_INPUTS='3918306b1935734f8e40375f1409a69ba10ef6c2262f13ce8bcb3ad5f82164d9'
EXPECTED_DISPATCHER='baef9c94e73b0310dda8ee5bc0d6881ef784e5c1a5e0cfe37866a14d9e2de2e4'
BOUNDS=dict(members=2048,file_bytes=64*2**20,logical_bytes=512*2**20,
            physical_bytes=384*2**20,compressed_bytes=192*2**20,expanded_bytes=416*2**20)


def require(ok,message):
    if not ok:raise RuntimeError(message)


def read(path):
    path=Path(path);require(path.stat().st_size<=64*2**20,'bounded evidence JSON required')
    return json.loads(path.read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def stamp(path):
    value=Path(path).lstat()
    return [value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_nlink]


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def check(path,row,maximum=BOUNDS['file_bytes']):
    path=Path(path);before=stamp(path)
    require(path.resolve(strict=True)==path and stat.S_ISREG(before[2]) and before==row['stamp']
        and before[3]==row['bytes']<=maximum and sha(path)==row['sha256'] and stamp(path)==before,
        'frozen publication input differs: '+str(path))


def main():
    require(all(type(value) is str and re.fullmatch('[a-f0-9]{64}',value)
        for value in [EXPECTED_LAUNCH,EXPECTED_INPUTS,EXPECTED_DISPATCHER]),'unbound source-only publication auditor')
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'exact audit owner/unoptimized -B')
    require(not OUT.exists() and not OUT.is_symlink(),'fresh independent audit required')
    started=time.time()
    require(sha(D/'launch.json')==EXPECTED_LAUNCH and sha(D/'inputs.json')==EXPECTED_INPUTS,'exact reviewed packet differs')
    freeze=read(D/'inputs.json');launch=read(D/'launch.json');receipt=read(W/'receipt.json')
    outer=read(O/'status.json');dispatcher=read(L/'record.json')
    require(freeze['owner']==str(ROOT) and freeze['bounds']==launch['bounds']==BOUNDS
        and launch['inputs_sha256']==receipt['inputs_sha256']==EXPECTED_INPUTS
        and launch['environment']==freeze['environment'] and type(launch['expected_workload_children']) is int
        and launch['expected_workload_children']==0 and freeze['workload_children']==0
        and freeze['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock' and freeze['wait_seconds']==600
        and freeze['capacity']==launch['capacity']==dict(entry_gib=9,stop_gib=9,floor_gib=8,reservation_bytes=416*2**20),
        'publication frozen scope differs')
    wanted=[freeze['python'],'-B',str(ROOT/'scripts/supervise_experiment.py'),'--run-id',O.name,'--',
        freeze['python'],'-B',str(D/'retain.py'),'--inputs-sha256',EXPECTED_INPUTS]
    require(launch['command']==wanted and outer['status']=='finished' and outer['returncode']==0
        and outer['command']==wanted[6:] and outer['cwd']==str(ROOT)
        and outer['plan_sha256']==sha(O/'plan.json') and outer['log_sha256']==sha(O/'command.log')
        and receipt['status']=='passed' and receipt['pid']==outer['child_pid'] and receipt['parent_pid']==outer['supervisor_pid']
        and outer['child_started_at']<=receipt['started_at']<=receipt['admitted_at']<=receipt['finished_at']<=outer['finished_at'],
        'actual zero-child publication owner/closure differs')
    require(all(type(receipt[key]) is int and receipt[key]==0 for key in ['workload_children','compiler_calls','B3_compositions'])
        and receipt['free_bytes_before']>=9*2**30+416*2**20 and receipt['free_bytes_after']>=9*2**30,
        'publication workload or resource bounds differ')
    require(dispatcher['status']=='terminal-observed' and dispatcher['returncode']==0 and dispatcher['launcher_returncode']==0
        and dispatcher['outer_status']=='finished' and dispatcher['outer_sha256']==sha(O/'status.json')
        and dispatcher['command']==wanted and dispatcher['environment']==launch['environment'] and dispatcher['cwd']==str(ROOT)
        and dispatcher['launch_sha256']==EXPECTED_LAUNCH and dispatcher['launcher_source_path']
            ==str(ROOT/'.work/launch_native_qualification_publication_01.py')
        and dispatcher['launcher_source_sha256']==sha(dispatcher['launcher_source_path'])==EXPECTED_DISPATCHER
        and dispatcher['controller_pid']==receipt['pid'] and dispatcher['supervisor_pid']==receipt['parent_pid']
        and dispatcher['started_at']<=outer['started_at'] and dispatcher['started_at']<=dispatcher['launcher_finished_at']
        <=dispatcher['terminal_observed_at']==dispatcher['finished_at'] and outer['finished_at']<=dispatcher['finished_at'],
        'bounded actual terminal observer differs')
    require(dispatcher['entry_free_bytes']>=9*2**30+416*2**20 and dispatcher['maximum_wrapper_seconds']==30
        and dispatcher['maximum_observation_seconds']==1800 and dispatcher['wrapper_identity_limitation']
            =='Popen PID retained; no separate contemporaneous wrapper ps/cwd probe.',
        'dispatcher actual finite bounds differ')
    identity=dispatcher['launcher_identity']
    require(identity['source']=='in-process observation' and identity['pid']==dispatcher['launcher_pid']
        and identity['parent_pid']==dispatcher['launcher_parent_pid'] and identity['cwd']==str(ROOT)
        and identity['argv']==[dispatcher['launcher_source_path']]
        and all(type(value) is int and value>0 for value in [identity['pid'],identity['parent_pid'],identity['pgid'],dispatcher['pid']]),
        'recorded dispatcher process identity differs')
    for name in ['stdout','stderr']:require(dispatcher[name+'_sha256']==sha(L/name),'dispatcher raw changed')
    handoff=read(L/'stdout')
    require(handoff==dispatcher['supervisor_handoff'] and handoff['supervisor_pid']==outer['supervisor_pid']
        and handoff['directory']==str(O),'actual supervisor handoff differs')
    for name,row in freeze['files'].items():check(name,row)
    for row in freeze['prior_archives']:check(row['path'],row,192*2**20)
    for name,resolved in freeze['routes'].items():require(str(Path(name).resolve(strict=True))==resolved,'executor route differs')
    for name in freeze['absent_paths']:require(not Path(name).exists() and not Path(name).is_symlink(),'failed namespace gained result')
    for name,row in freeze['directories'].items():
        root=Path(name);require(root.resolve(strict=True)==root and root.is_dir(),'ordinary evidence root required');found=[]
        for path in root.rglob('*'):
            require(not path.is_symlink() and (path.is_file() or path.is_dir()),'indirect evidence member')
            if path.is_file() and str(path) not in row['excluded_future_outputs']:found.append(str(path))
        require(sorted(found)==row['members'],'complete evidence membership differs')
    history=ModuleType('_native_publication_history_audit');history.__file__=str(D/'history.py')
    source=(D/'history.py').read_bytes();require(hashlib.sha256(source).hexdigest()==freeze['files'][str(D/'history.py')]['sha256'],
        'executed pure history source changed')
    sys.modules[history.__name__]=history;exec(compile(source,history.__file__,'exec'),history.__dict__)
    require(encoded(history.validate_all())==encoded(freeze['history']),'complete31/native20/control/snapshot history differs')
    summary=read(RESULT/'summary.json');manifest=read(RESULT/'manifest.json');archive=RESULT/'evidence.tar.gz'
    require(summary['status']=='passed' and encoded(summary['history'])==encoded(freeze['history']) and summary['inputs_sha256']==EXPECTED_INPUTS
        and summary['manifest_sha256']==sha(RESULT/'manifest.json') and receipt['summary_sha256']==sha(RESULT/'summary.json')
        and summary['original_failures_preserved'] is True and receipt['archive']==summary['archive']
        and summary['prior_archives']==freeze['prior_archives'] and summary['payload_exclusions']==freeze['payload_exclusions']
        and sha(archive)==summary['archive']['sha256'] and archive.stat().st_size==summary['archive']['bytes']<=192*2**20,
        'actual lossless archive summary differs')
    expected={name.lstrip('/'):freeze['files'][name] for name in freeze['archive_sources']}
    expected[str(D/'inputs.json').lstrip('/')]=dict(bytes=(D/'inputs.json').stat().st_size,sha256=EXPECTED_INPUTS)
    require(set(expected)==set(manifest) and len(expected)==summary['archive']['logical_members']<=2048,'exact archive member set differs')
    seen=set();physical=0;logical=0;physical_bytes=0;first={}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            require(member.name in expected and member.name not in seen,'unexpected or duplicate archive member')
            row=manifest[member.name];want=expected[member.name]
            require(row['source']=='/'+member.name and row['sha256']==want['sha256'] and row['bytes']==want['bytes'],
                'archive source/size/hash mapping differs')
            key=(want['sha256'],want['bytes'])
            if 'linkname' in row:
                require(member.islnk() and member.linkname==row['linkname'] and member.linkname in seen and member.size==0
                    and key in first and first[key]==member.linkname,
                    'archive alias does not name an earlier retained member')
            else:
                require(member.isfile() and member.size==row['bytes'] and key not in first,'archive payload type/size/dedup differs')
                physical+=1;physical_bytes+=member.size;first[key]=member.name
            count=0;hasher=hashlib.sha256()
            with tar.extractfile(member) as stream:
                while block:=stream.read(2**20):
                    count+=len(block);require(count<=64*2**20,'bounded archive member readback');hasher.update(block)
            require(count==row['bytes'] and hasher.hexdigest()==row['sha256'],'full logical archive bytes differ')
            seen.add(member.name);logical+=count
    require(seen==set(expected) and physical==summary['archive']['physical_members']
        and logical<=512*2**20 and physical_bytes==sum(size for _,size in first)<=384*2**20,'all logical aliases and physical payloads required')
    expanded=0
    with gzip.open(archive,'rb') as stream:
        while block:=stream.read(2**20):expanded+=len(block);require(expanded<=416*2**20,'finite full gzip EOF readback')
    require(expanded==summary['archive']['expanded_bytes'] and summary['archive']['full_member_hashes_verified'] is True
        and summary['archive']['full_gzip_eof_crc_verified'] is True,'full archive verification flags differ')
    copies=freeze['source_copies'];copy_result=summary['source_copies'];source_map=read(SOURCES/'source-map.json')
    require(len(copies)==58 and sum(row['size'] for row in copies.values())==512816
        and copy_result['directory']==str(SOURCES) and copy_result['files']==source_map['files']==copies
        and copy_result['bytes']==512816 and copy_result['source_map_sha256']==sha(SOURCES/'source-map.json')
        and source_map['status']=='exact-source-copies','exact standalone source copy declaration differs')
    observed=[]
    for path in SOURCES.rglob('*'):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),'indirect source-copy entry')
        if path.is_file():observed.append(str(path))
    require(set(observed)==set(copies)|{str(SOURCES/'source-map.json')},'exact source-copy membership differs')
    for name,row in copies.items():
        path=Path(name);before=stamp(path)
        require(path.resolve(strict=True)==path and stat.S_ISREG(before[2]) and before[3]==row['size'] and before[6]==1
            and sha(path)==row['sha256']==freeze['files'][row['source']]['sha256'] and stamp(path)==before
            and before[:2]!=freeze['files'][row['source']]['stamp'][:2], 'source copy differs or aliases original inode')
    for name,row in freeze['files'].items():check(name,row)
    for row in freeze['prior_archives']:check(row['path'],row,192*2**20)
    require(set(p.name for p in RESULT.iterdir())=={'evidence.tar.gz','manifest.json','summary.json'},'fresh result membership differs')
    report=dict(status='verified',receipt_sha256=sha(W/'receipt.json'),summary_sha256=sha(RESULT/'summary.json'),
        manifest_sha256=sha(RESULT/'manifest.json'),archive_sha256=sha(archive),inputs_sha256=EXPECTED_INPUTS,
        logical_members=len(expected),physical_members=physical,logical_bytes=logical,physical_bytes=physical_bytes,expanded_bytes=expanded,
        full_gzip_eof_crc=True,full_member_readback=True,all376_inner_gzip_readback=True,all125_delta_logical_members=True,
        source_copies=58,source_copy_bytes=512816,source_map_sha256=sha(SOURCES/'source-map.json'),
        history=freeze['history'],retention_workload_children=0,inputs=len(freeze['files']),
        wrapper_identity_limitation=dispatcher['wrapper_identity_limitation'],verifier_sha256=sha(Path(__file__).resolve()),
        started_at=started,finished_at=time.time())
    data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();require(len(data)<=2*2**20,'bounded independent publication audit')
    with OUT.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    require(OUT.read_bytes()==data,'audit publication readback differs')
    print(json.dumps(dict(path=str(OUT),sha256=sha(OUT),logical_members=len(expected),physical_members=physical)))


if __name__=='__main__':main()

"""Finite saved metadata/build readback; no target imports or provider probes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = ROOT/'experiments/runtime-exporter-after-installation07-02'
MW = X/'.work/hir-options-hash-exporter-metadata-02'
BW = X/'.work/hir-options-hash-exporter-build-02'
OUT = X/'.work/runtime-exporter07-metadata-build02-independent-readback-01.json'
FILES = {}
RAW = {}


def stamp(p):
    s = p.lstat()
    return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]


def raw(path, digest=None):
    p=Path(path); before=stamp(p)
    assert p.resolve(strict=True)==p and stat.S_ISREG(before[2]) and before[6]==1
    assert 0<=before[3]<=8*2**20
    with p.open('rb') as f:
        data=f.read(8*2**20+1);assert f.read(1)==b''
    assert stamp(p)==before and len(data)==before[3]
    row=dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=before)
    assert digest is None or row['sha256']==digest,(p,'digest')
    FILES[str(p)]=row;RAW[str(p)]=data
    return data


def read(path,digest=None):
    return json.loads(raw(path,digest))


def reference(ref):
    raw(ref['path'],ref['sha256'])
    assert FILES[ref['path']]==ref


def dyld(data,pid,allowed,driver,expected):
    images={};events=[];offset=0
    for number,line in enumerate(data.splitlines(keepends=True),1):
        assert line.endswith(b'\n') and not line.endswith(b'\r\n')
        text=line[:-1].decode();e=dict(line=number,start=offset,end=offset+len(line),raw_hex=line.hex())
        match=re.fullmatch(r'dyld\[([1-9][0-9]*)\]: <([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})> (/[^\x00\r\n]+)',text)
        if match:
            assert int(match[1])==pid;path=match[3];assert path not in images
            system=path.startswith(('/usr/lib/','/System/Library/'));assert system or path in allowed
            images[path]=dict(path=path,uuid=match[2],state='loaded',system=system,load_event=len(events))
            e.update(kind='load',path=path,uuid=match[2],state='loaded')
        else:
            match=re.fullmatch(r'dyld\[([1-9][0-9]*)\]: move (loaded to delayed|delayed to loaded): ([^/\x00\r\n]+)',text)
            assert match and int(match[1])==pid
            matches=[p for p in images if p.rsplit('/',1)[-1]==match[3]];assert len(matches)==1
            path=matches[0];before,after=match[2].split(' to ');assert images[path]['state']==before
            images[path]['state']=after;e.update(kind='transition',path=path,basename=match[3],before=before,after=after)
        events.append(e);offset+=len(line)
    assert driver in allowed and images[driver]['state']=='loaded'
    result=dict(policy='dyld-loaded-delayed-events-v1',pid=pid,raw_sha256=hashlib.sha256(data).hexdigest(),raw_bytes=len(data),events=events,images=list(images.values()),loaded=[p for p,v in images.items() if v['state']=='loaded'],delayed=[p for p,v in images.items() if v['state']=='delayed'],selected_driver=driver,selected_driver_active=True)
    assert offset==len(data) and result==expected
    return dict(events=len(events),images=len(images),loaded=len(result['loaded']),delayed=len(result['delayed']),driver=driver)


def main():
    packet=H/'packet-01'
    plan=read(packet/'plan.json','b73d54be6a0d561251bfa522eceb66c5fff21431554699b7d117ce0afa2ac32a')
    inputs=read(packet/'inputs.json','7265eb79a4285dceadb1951f19b975cbf93c84cf65439d2f2602a6a149ddec8a')
    launch=read(packet/'launch.json','5fc9f8acda80fc34f799be9f8fa8502f902af8b40eb0b9b87004b6df1fda4185')
    assert launch['plan']==inputs['plan'];reference(launch['plan']);reference(launch['inputs'])
    roles=read(packet/'compiler-roles.json');assert roles==plan['binding']
    source_sha='1517b945e4ef190aa9960db4b62564a5da5dc922260501f8306ce38fb591c044'
    build_sha='bce87300954ed5eefddfb80cb7a43e6f467be37e0e440838dc023c87fb7db589'
    for name,digest,count in [('sources.json',source_sha,11),('build-sources.json',build_sha,15)]:
        manifest=read(H/name,digest);assert len(manifest['files'])==count
        for path,sha in manifest['files'].items():raw(path,sha)
    raw(H/'execute.py','304e8777c0f8b9fff85ea90ed25b4ed7a154715a434dc8779b4ab8a06a9fd573')
    for row in plan['source_materialization'].values():reference(row)
    assert len(plan['source_materialization'])==238
    target=X/'.work/hir-options-hash-exporter-target-02';names=['rust-interp-mir-export','rust-interp-rustc-wrapper']
    future=plan['future_build'];schedule=[dict(label='cargo-build',command=future['command'],cwd=future['cwd'],environment=future['environment'],expected=[0])]
    for name in names:
        for flag in ['-L','-l']:schedule.append(dict(label=name+flag,command=['/usr/bin/otool','-arch','arm64',flag,str(target/'release'/name)],cwd=str(X),environment=plan['launch_environment'],expected=[0]))
    schedule += [dict(label='exporter-capabilities',command=[str(target/'release'/names[0]),'--rust-interp-capabilities'],cwd=str(X),environment=plan['launch_environment']|{'DYLD_PRINT_LIBRARIES':'1'},expected=[0]),dict(label='wrapper-roles',command=[str(target/'release'/names[1]),'--rust-interp-compiler-roles'],cwd=str(X),environment=plan['launch_environment'],expected=[0])]
    phases={};outcomes={};loader={}
    for phase,work,expected,count,pids in [('metadata',MW,plan['children'],36,(97343,98056,98058)),('build',BW,schedule,7,(53853,54567,54569))]:
        ep=ROOT/'.work'/('runtime-exporter07-'+phase+'-execution-02');outer=X/'.work/experiments'/('hir-options-hash-exporter-'+phase+'-supervisor-02')
        e=read(ep/'record.json');s=read(outer/'status.json',e['outer_status_sha256']);op=read(outer/'plan.json',e['outer_plan_sha256']);t=read(work/'receipt.json')
        assert (e['parent_pid'],e['pid'],t['pid'])==pids
        assert e['status']=='finished' and e['returncode']==e['controller_returncode']==0 and e['controller_may_be_live'] is e['supervisor_may_be_live'] is False
        assert e['source_sha256']==FILES[str(H/'execute.py')]['sha256'] and e['launch_sha256']==FILES[str(packet/'launch.json')]['sha256']
        assert e['command']==['/opt/homebrew/bin/python3','-B',str(X/'scripts/supervise_experiment.py'),'--supervise',str(outer/'plan.json')]
        assert e['cwd']==str(X) and e['environment']==launch['environment'] and e['signals']==e['retries']==0
        assert raw(ep/'stdout',e['stdout_sha256'])==raw(ep/'stderr',e['stderr_sha256'])==b''
        raw(outer/'command.log',s['log_sha256'])
        assert s['status']=='finished' and s['returncode']==0 and s['supervisor_pid']==pids[1] and s['supervisor_parent_pid']==pids[0] and s['child_pid']==pids[2]
        assert s['plan_sha256']==e['outer_plan_sha256'] and s['command']==op['command'] and s['owner']==s['cwd']==op['owner']==str(X)
        assert t['command']==s['command'][2:] and t['parent_pid']==pids[1] and t['cwd']==str(X) and t['status']=='passed' and t['phase']==phase
        assert e['started_at']<=e['child_started_at']<=s['started_at']<=s['child_started_at']<=t['started_at']<=t['admitted_at']<=t['finished_at']<=s['finished_at']<=e['finished_at']
        assert t['sources_sha256']==source_sha and t['inputs_sha256']==FILES[str(packet/'inputs.json')]['sha256'] and t['plan_sha256']==FILES[str(packet/'plan.json')]['sha256'] and t['runtime_key']==plan['runtime_key']
        assert t['signals']==t['retries']==t['compiler_builds']==t['VM_builds']==t['guest_executions']==0 and t['application_qualified'] is t['performance_measurement'] is False
        assert t['entry_free_bytes']>=16*2**30 and t['free_bytes_after']>=8*2**30 and len(t['commands'])==len(expected)==count
        previous=t['admitted_at'];got={}
        for index,(ref,wanted) in enumerate(zip(t['commands'],expected,strict=True)):
            path=work/'commands'/f'{index:03d}'/'receipt.json';assert ref['path']==str(path) and ref['label']==wanted['label']
            child=read(path,ref['sha256']);assert child['status']=='finished' and child['returncode']==ref['returncode']==0 and child['pid']==ref['pid']
            assert child['command']==wanted['command'] and child['cwd']==wanted['cwd'] and child['environment']==wanted['environment'] and child['supervisor_pid']==pids[2] and child['parent_pid']==pids[1]
            assert previous<=child['started_at']<=child['finished_at']<=t['finished_at'];previous=child['finished_at']
            assert child['free_bytes_before']>=9*2**30 and child['free_bytes_after']>=8*2**30
            assert all(child['started_at']<=z['time']<=child['finished_at'] and z['free_bytes']>=9*2**30 for z in child['disk_samples'])
            assert child['identity']['ps_returncode']==0
            assert child['identity']['ps'].split()[:3]==[str(child['pid']),str(pids[2]),str(child['pid'])]
            if child['identity']['cwd_returncode']==0:
                assert 'n'+child['cwd']+'\n' in child['identity']['cwd']
            else:
                assert child['identity']['cwd_returncode']==1 and child['identity']['cwd']==''
            stdout=raw(path.parent/'stdout',child['stdout_sha256']);stderr=raw(path.parent/'stderr',child['stderr_sha256'])
            if wanted.get('expected_stdout_sha256') is not None:assert child['stdout_sha256']==wanted['expected_stdout_sha256'] and not stderr
            got[wanted['label']]=dict(path=path,receipt=child,stdout=stdout,stderr=stderr)
            argv=child['command']
            if argv[:3]==['/usr/bin/otool','-arch','arm64']:assert not stderr;loader[(argv[-1],argv[3])]=stdout.decode()
        reference(t['result']);result=read(t['result']['path']);phases[phase]=dict(execution=e,outer=s,terminal=t,result=result);outcomes[phase]=got
    m=phases['metadata']['result'];b=phases['build']['result'];mt=phases['metadata']['terminal'];bt=phases['build']['terminal']
    assert mt['finished_at']<=bt['started_at'] and bt['metadata_receipt_sha256']==FILES[str(MW/'receipt.json')]['sha256'] and bt['build_sources_sha256']==build_sha
    assert mt['exporter_builds']==0 and bt['exporter_builds']==1 and bt['frontend_qualified'] is bt['published'] is False
    assert m['status']=='metadata-passed-build-unexecuted' and m['binding']==roles and m['actual_children']==36 and m['plan_sha256']==inputs['plan']['sha256']
    assert b['status']=='build-passed-frontend-unexecuted' and b['compiler_roles']==roles and b['runtime_key']==plan['runtime_key'] and b['runtime_owner']==plan['runtime_owner'] and b['VM']==plan['adopted_VM']
    assert b['frontend_qualified'] is b['application_qualified'] is b['published'] is b['performance_measurement'] is False
    assert b['metadata']==bt['metadata'];reference(b['metadata']['receipt']);reference(b['metadata']['result'])
    for name,row in b['built_files'].items():assert name in names and row['path']==str(target/'release'/name);reference(row);assert b['binaries'][name]==row['sha256']
    assert set(b['built_files'])==set(names) and b['binaries']['rust-interp-vm']==plan['adopted_VM']['binary']['sha256']
    for ref in b['generated']+[b['evidence'],b['exporter_probe'],b['wrapper_probe']]:reference(ref)
    evidence=read(b['evidence']['path']);assert evidence['generated']==b['generated'] and evidence['build_script_compiler_identity_probes']==4 and evidence['strip_failures']==0
    assert evidence['cargo_receipt']==FILES[str(BW/'commands/000/receipt.json')]
    cg=outcomes['build']['cargo-build'];parsed=evidence['parsed'];assert ''.join(z['raw'] for z in parsed['rows']).encode()==cg['stdout']
    messages=[];forwarded=[];labels={f"[{z['name']} {z['version']}] ":z['id'] for z in m['dependencies']['packages']}
    for n,line in enumerate(cg['stdout'].decode().splitlines(keepends=True),1):
        row=parsed['rows'][n-1];assert row['line']==n and row['raw']==line
        if line.startswith('{'):obj=json.loads(line);assert row==dict(line=n,kind='cargo-json',raw=line,message=obj);messages.append(obj)
        else:
            hits=[(k,v) for k,v in labels.items() if line.startswith(k)];assert len(hits)==1;key,value=hits[0];assert row==dict(line=n,kind='build-script-stdout',raw=line,package_id=value,prefix=key);forwarded.append(row)
    assert messages==parsed['messages'] and forwarded==parsed['forwarded'] and messages[-1]=={'reason':'build-finished','success':True}
    executed={z['package_id'] for z in messages if z['reason']=='build-script-executed'};assert all(z['package_id'] in executed for z in forwarded)
    compiled=[]
    assert not any(v in cg['stderr'] for v in [b'stripping debug info',b'SIGABRT',b'Library not loaded:',b'internal compiler error'])
    for line in cg['stderr'].decode().splitlines():
        match=re.fullmatch(r'\s*Running `(.*)`',line)
        if not match:continue
        argv=shlex.split(match[1])
        if '--crate-name' not in argv:continue
        d=roles['build']['executable']['path'];assert argv.count(d)==1;j=argv.index(d);command=argv[j:];pre=argv[:j];assign=pre[1:] if pre[:1]==['env'] else pre;assert all('=' in z for z in assign)
        assert all(z in command for z in roles['build_rustflags']) and sum(z.startswith('--sysroot') for z in command)==1 and not any('RUSTC_FORCE_RUSTC_VERSION=' in z or 'RUSTC_OVERRIDE_VERSION_STRING=' in z for z in argv)
        ss=[z for z in command if z.endswith('.rs')];assert len(ss)==1;source=Path(ss[0]);source=source if source.is_absolute() else Path(plan['source_root'])/source;source=os.path.normpath(source);assert source in plan['files']
        compiled.append(dict(command=command,environment_assignments=argv[:j],source=source))
    assert compiled==evidence['compilers'] and len(compiled)==44
    artifacts=[z for z in messages if z['reason']=='compiler-artifact' and 'bin' in z.get('target',{}).get('kind',[]) and z.get('executable')]
    assert {z['executable'] for z in artifacts}=={z['path'] for z in b['built_files'].values()}
    for name,row in b['built_files'].items():assert len([z for z in artifacts if z['executable']==row['path'] and z['target']['name']==name and z['fresh'] is False])==1
    generated=RAW[b['generated'][0]['path']].decode();literal=generated.split('Some(',1)[1].split(');',1)[0];assert json.loads(json.loads(literal))==roles
    caps=json.loads(outcomes['build']['exporter-capabilities']['stdout']);assert 'runtime_wrapper' not in caps
    assert caps|{'runtime_wrapper':dict(sha256=b['binaries'][names[1]],compiler_roles=roles)}==b['capabilities'] and caps['compiler_roles']==roles and caps['compiler_sysroot']==roles['runtime']['default_sysroot'] and caps['schema_version']==1 and caps['bytecode_version']==5
    assert not outcomes['build']['wrapper-roles']['stderr'] and json.loads(outcomes['build']['wrapper-roles']['stdout'])==roles
    cm=json.loads(outcomes['metadata']['cargo-metadata']['stdout']);assert not outcomes['metadata']['cargo-metadata']['stderr'] and cm['target_directory']==plan['metadata_target'] and cm['workspace_root']==plan['source_root']
    assert m['dependencies']==dict(packages=cm['packages'],resolve=cm['resolve']) and len(cm['packages'])==30
    assert raw(MW/'cargo-metadata.json')==outcomes['metadata']['cargo-metadata']['stdout']
    observations=[]
    for label,v in outcomes['metadata'].items():
        cmd=v['receipt']['command']
        if cmd[:3]==['/usr/bin/otool','-arch','arm64']:observations.append(dict(path=cmd[-1],flag=cmd[3],receipt=str(v['path']),stdout_sha256=v['receipt']['stdout_sha256']))
    assert sorted(observations,key=lambda z:(z['path'],z['flag']))==m['loader_observations']
    closure_rows=list(m['closures'].items())+[(str(target/'release'/name),closure) for name,closure in b['tool_closures'].items()]
    for executable,closure in closure_rows:
        ident=closure['identity'];assert ident['platform']==plan['platform'] and ident['policy']=='macos-dyld-closure-v1'
        for lib in ident['libraries']:
            frozen=plan['files'][lib['resolved']];assert lib['sha256']==frozen['sha256'] and lib['bytes']==frozen['bytes']
        for name,node in ident['nodes'].items():
            resolved=executable if name=='$CARGO' else os.path.normpath(name)
            if (resolved,'-L') not in loader:resolved=plan['routes'].get(resolved,resolved)
            text=loader[(resolved,'-L')];tokens=[z.strip().split(' (compatibility version ',1)[0] for z in text.splitlines() if z.startswith('\t')];paths=[];active=False
            for line in loader[(resolved,'-l')].splitlines():
                if line.strip().startswith('cmd '):active=line.strip()=='cmd LC_RPATH'
                elif active and (match:=re.match(r'\s*path (.+) \(offset \d+\)',line)):paths.append(match[1])
            assert node==dict(dependencies=tokens,rpaths=paths)
    driver=roles['runtime_driver']['path'];admitted={driver,str(Path(roles['runtime']['default_sysroot'])/'lib/libLLVM.dylib')}
    assert {z['resolved'] for z in b['tool_closures'][names[0]]['identity']['libraries']}==admitted and b['tool_closures'][names[1]]['identity']['libraries']==[]
    dyld_rows={}
    for role in ['build','runtime']:
        version=outcomes['metadata'][role+'-version'];sysroot=outcomes['metadata'][role+'-sysroot'];path=roles[role]['executable']['path'];saved=m['actual_roles'][role]
        assert saved['closure']==m['closures'][path] and saved['version_receipt']==str(version['path']) and saved['sysroot_receipt']==str(sysroot['path'])
        assert version['stdout'].decode()==roles[role]['verbose_version'] and not sysroot['stderr'] and sysroot['stdout'].decode()==roles[role]['default_sysroot']+'\n'
        allowed={path}|{z['resolved'] for z in saved['closure']['identity']['libraries']};drivers=[z for z in allowed if Path(z).name.startswith('librustc_driver-')];assert len(drivers)==1
        dyld_rows[role]=dyld(version['stderr'],version['receipt']['pid'],allowed,drivers[0],saved['loaded'])
    cap=outcomes['build']['exporter-capabilities'];dyld_rows['exporter']=dyld(cap['stderr'],cap['receipt']['pid'],{str(target/'release'/names[0])}|admitted,driver,b['exporter_loader'])
    for path,row in FILES.items():assert stamp(Path(path))==row['identity']
    report=dict(status='verified-closed-metadata-and-build',reviewer='/root/workspace_capacity',observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),parent_pid=os.getppid(),checked_files=FILES,phase_refs={phase:dict(execution=FILES[str(ROOT/'.work'/('runtime-exporter07-'+phase+'-execution-02')/'record.json')],receipt=FILES[str(work/'receipt.json')],result=phases[phase]['terminal']['result']) for phase,work in [('metadata',MW),('build',BW)]},metadata_children=36,build_children=7,cargo_compiles=44,source_files_rehashed=238,built_files=b['built_files'],generated=b['generated'],dyld=dyld_rows,provider_payloads_rehashed=0,compiler_calls=0,provider_probes=0,frontend_qualified=False,application_qualified=False,performance_qualified=False,limitations=['Four real build-script identity probes are bound through unchanged source, generated role output and Cargo history, not separately supervised child receipts.','Recorded loader nodes are matched to exact saved otool raw and resolved-library hashes/sizes to the frozen packet. Provider filesystem resolution/content is not rerun.','VM is the explicitly adopted historical binary reference; this readback rehashes the two newly built tools, not provider or VM payloads.','Active frontend outputs are excluded.'])
    with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
    raw(OUT);print(json.dumps(FILES[str(OUT)],sort_keys=True))


if __name__=='__main__':main()

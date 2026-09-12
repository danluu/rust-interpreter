"""Qualify timing transparency, then measure original token source edits."""
import math
import run as common
from run import *
from bench_e2e_workflow import guest_test_failure

RUN='export-costs-token-01'


def timers(stderr):
    values=[json.loads(line.split(': ',1)[1]) for line in stderr.splitlines()
            if line.startswith('rust-interp-export-timings: ')]
    require(len(values)==2 and {v['scope'] for v in values}=={'emit','lower'},'missing/duplicate timing scopes')
    for v in values:
        require(v['schema_version']==1 and len({s['name'] for s in v['stages']})==len(v['stages']),'invalid timer schema')
        require(all(math.isfinite(s['seconds']) and s['seconds']>=0 for s in v['stages']),'invalid stage duration')
        require(abs(sum(s['seconds'] for s in v['stages'])-v['total_seconds'])<1e-8,'exclusive stage sum differs')
    return values


def qualify(work,tools,retained,env):
    fixture=ROOT/'tests/caller_fixture.rs';native=work/'native';commands=[];artifacts=[]
    seeds=['0','7',str(2**64-1)]
    r,_,_=invoke(work,'native-build',['rustc','+nightly-2026-09-08',fixture,'--edition=2024','-C','overflow-checks=off','-o',native],env)
    require(r['returncode']==0,'native fixture build failed');commands.append(r)
    r,out,_=invoke(work,'native-execute',[native,*seeds],env);commands.append(r)
    require(r['returncode']==0 and len(out.splitlines())==3,'native fixture failed');expected=out.splitlines()
    for label,exporter,enabled in [('retained',retained/'rust-interp-mir-export',False),
                                   ('off',tools/'rust-interp-mir-export',False),('on',tools/'rust-interp-mir-export',True)]:
        artifact=work/(label+'.rbc');export_env=dict(env,RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_OUTPUT=str(artifact),RUST_INTERP_INLINE_LEAVES='1')
        if enabled:export_env['RUST_INTERP_EXPORT_TIMINGS']='1'
        r,_,err=invoke(work,'fixture-'+label,[exporter,fixture,'--crate-name','timing_fixture','--edition=2024','--emit=metadata',
            '-C','overflow-checks=off','-Zmir-opt-level=3','-Zinline-mir-threshold=400','-Zinline-mir-hint-threshold=800','-Zinline-mir-forwarder-threshold=240',
            '-o',artifact.with_suffix('.rmeta')],export_env);commands.append(r)
        require(r['returncode']==0 and artifact.exists(),'fixture export failed')
        if enabled:timers(err)
        else:require('rust-interp-export-timings:' not in err,'disabled timers emitted diagnostics')
        artifacts.append(sha(artifact))
        for engine,flags in [('interpreter',['--engine','interpreter']),('jit',['--engine','jit','--jit-resumable-calls','--jit-persistent-registers'])]:
            for seed,want in zip(seeds,expected):
                r,out,_=invoke(work,label+'-'+engine+'-'+seed,[tools/'rust-interp-vm',*flags,artifact,seed],env);commands.append(r)
                require(r['returncode']==0 and out.strip()==want,'fixture/native result differs')
    require(len(set(artifacts))==1,'instrumentation changed fixture bytecode')
    for label,body in [('type','fn unused() { let _: u64 = "wrong"; }'),
                       ('borrow','fn unused() { let mut x=1; let a=&mut x; let b=&mut x; *a+=*b; }')]:
        source=work/(label+'.rs');source.write_text('pub fn entry()->u64 { 1 }\n'+body+'\n')
        artifact=work/(label+'.rbc');artifact.write_bytes(b'stale')
        r,_,err=invoke(work,'reject-'+label,[tools/'rust-interp-mir-export',source,'--crate-type=lib','--edition=2024','--emit=metadata','-o',artifact.with_suffix('.rmeta')],
                      dict(env,RUST_INTERP_EXPORT_TIMINGS='1',RUST_INTERP_ENTRY='entry',RUST_INTERP_OUTPUT=str(artifact)));commands.append(r)
        require(r['returncode']!=0 and not artifact.exists() and 'internal compiler error' not in err,'uncalled checking or stale-output rejection failed')
    write(work/'qualification.json',dict(status='passed',commands=commands,identical_artifact_sha256=artifacts[0],vm_native_comparisons=18,strict_rejections=2))


def profile(work,tools,key,env):
    reference=read(ROOT/'results/scalar-edit-smoke-01-token-phrase/summary.json')
    original_rows=read(ROOT/reference['raw']/'records.json')
    references={r['state']:r for r in original_rows if r['mode']=='baseline'}
    require(set(references)=={0,-1,1,2,3,4,5},'incomplete retained reference')
    case=WORKFLOW_VARIANTS[reference['project'],reference['workflow']]
    source=ROOT/'.work/sources/fre';marker=read(source/'.rust-interp-owned.json')
    require(marker['owner']==str(ROOT) and marker['revision']==reference['revision'],'source ownership differs')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==marker['revision'] and
            not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip(),'source is not the original pin')
    path=source/case['file'];original=path.read_bytes()
    command=list(references[0]['calls'][0]['command']);command[1]=str(HERE/'launcher.py')
    command[command.index('--tool-key')+1]=key;command[command.index('--cache-namespace')+1]=RUN
    env=dict(env,RUST_INTERP_LAUNCH_STATS='1',RUSTFLAGS=references[0]['calls'][0]['rustflags'],
             CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0',CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
    inventory=read(ROOT/'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json')
    cache_bytes=sum(g['bytes'] for g in inventory['manifest']['groups'])
    max_artifact=max((ROOT/r['artifacts'][0]['path']).stat().st_size for r in references.values())
    minimum=8*1024**3+((cache_bytes+2*max_artifact)*120+99)//100+16*1024**2
    free=shutil.disk_usage(ROOT).free
    write(work/'admission.json',dict(required_free_bytes=minimum,observed_free_bytes=free,cache_reference_bytes=cache_bytes,max_artifact_bytes=max_artifact,
        growth_percent=20,note='Reuse existing immutable snapshots if hashes match; preserve first mismatching output and stop. One fresh metadata cache.'))
    require(free>=minimum,'insufficient diagnostic space; no source edit started')
    records=[]
    with SourceEdit(path,original) as edit:
        for state in source_states(original.decode(),case,1,['native','baseline','candidate'],True):
            edit.replace(state['source'])
            r,out,err=invoke(work,'state-'+str(state['state']),command,env)
            r.update(state=state['state'],source_sha256=sha(path),timings=timers(err))
            require(r['source_sha256']==references[state['state']]['source_sha256'],'source edit differs from reference')
            require((r['returncode']==0)==(state['state']!=-1),'original runtime outcome changed')
            require(guest_test_failure(err) if state['state']==-1 else out.strip()=='0','original assertion result differs')
            launched=[json.loads(l.split(': ',1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
            require(len(launched)==1,'missing launch receipt');launch=launched[0];artifact=Path(launch['artifact_path'])
            require(launch['tool_key']==key and launch['jit_resumable_calls'] and launch['jit_persistent_registers'],'wrong observer runtime')
            previous=references[state['state']]['artifacts'][0];r.update(artifact_sha256=sha(artifact),reference_artifact=previous['path'],launch=launch)
            if r['artifact_sha256']!=previous['sha256']:
                shutil.copy2(artifact,work/'mismatching-artifact.rbc');write(work/'mismatch.json',r)
                raise RuntimeError('observer artifact differs from retained history; preserve and investigate')
            require(sha(ROOT/previous['path'])==previous['sha256'],'saved reference artifact changed')
            records.append(r);write(work/'records.json',records)
            print('state',state['state'],'command',round(r['seconds'],3),'artifact identical',flush=True)
    require(path.read_bytes()==original,'source restoration failed')
    medians={}
    for scope in ['emit','lower']:
        stages=[next(t for t in r['timings'] if t['scope']==scope) for r in records if r['state']>0]
        names=[s['name'] for s in stages[0]['stages']]
        require(all([s['name'] for s in t['stages']]==names for t in stages),'stage shape changed')
        medians[scope]={n:statistics.median(next(s['seconds'] for s in t['stages'] if s['name']==n) for t in stages) for n in names}
    return dict(status='passed',tool_key=key,commands=len(records),edited_samples=5,original_assertions_pass=True,
                wrong_edit_rejected=True,source_restored=True,all_artifact_hashes_identical=True,stage_medians=medians,
                raw=str(work.relative_to(ROOT)),records_sha256=sha(work/'records.json'),qualification_sha256=sha(work/'qualification.json'),
                note='Instrumented diagnostic. Exclusive stages within each scope; lower is nested in emit.lower_graph. No speedup or cold comparison.')


def main():
    work=ROOT/'.work'/RUN;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            build=read(ROOT/'results/export-costs-build-02/summary.json')
            require(build['status']=='passed' and read(ROOT/'.work/experiments/export-costs-build-02/status.json').get('returncode')==0,'observer build not terminal')
            tools,key=installed_tools(build['tool_key']);retained,_=installed_tools(CONTROL);env=environment()
            paths=[HERE/n for n in ['run.py','profile.py','launcher.py','PLAN.md']]
            paths += [ROOT/'scripts'/n for n in ['interpreter.py','workflow_io.py','workflow_measurements.py','workflow_cases.py','std_mir.py']]
            paths += [ROOT/'results/export-costs-build-02/summary.json',ROOT/'results/scalar-edit-smoke-01-token-phrase/summary.json']
            frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
            write(work/'plan.json',dict(tool_key=key,frozen=frozen,source_commit=build['source_commit'],stage_intervals='exclusive within each nested scope'))
            qualify(work,tools,retained,env)
            result=profile(work,tools,key,env)
            require(all(sha(ROOT/p)==h for p,h in frozen.items()),'profile input changed')
            result['frozen']=frozen
            out=ROOT/'results'/RUN;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(result['stage_medians'],flush=True)
    except BaseException as error:
        status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()

"""Current-host adopted/candidate comparison after preserved historical drift."""
import ctypes,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/compact-switch-adopted-profile'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from native_observation import logical_counts
from qualify import validate_case
RUN='compact-switch-current-host-01'
OLD='compact-switch-adopted-profile-01'
KEY='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
VM_HASH='6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'
def read(p):return json.loads(p.read_text())
def stats(raw,index):return {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',(raw/f'{index}.stderr').read_text())}
def host():
    lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True);query=lib.sysctlbyname
    query.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t];query.restype=ctypes.c_int
    rows=[]
    for name in ['hw.optional.arm.FEAT_FAMINMAX','hw.optional.arm.FEAT_LUT']:
        value=ctypes.c_uint32(0);length=ctypes.c_size_t(4);ctypes.set_errno(0)
        rc=query(name.encode(),ctypes.byref(value),ctypes.byref(length),None,0)
        rows.append(dict(name=name,returncode=rc,errno=ctypes.get_errno(),value=value.value,length=length.value))
    return dict(sw_vers=subprocess.check_output(['/usr/bin/sw_vers'],text=True),uname=list(os.uname()),queries=rows)
def drift(current,previous):
    assert len(current['functions'])==len(previous['functions'])
    a,ta=logical_counts(current);b,tb=logical_counts(previous);changes=[]
    for i,(x,y,ca,cb) in enumerate(zip(current['functions'],previous['functions'],a,b)):
        for k in ['name','frame_size','registers','operations']:assert x[k]==y[k]
        delta=[dict(pc=pc,current=u,historical=v,delta=u-v) for pc,(u,v) in enumerate(zip(ca,cb)) if u!=v]
        if delta:changes.append(dict(function=i,name=x['name'],pcs=delta,delta=sum(c['delta'] for c in delta)))
    assert all(c['name'] in ['fre_target_features::macos::detect_aarch64[]','fre_target_features::macos::integer[]'] for c in changes),changes
    assert ta['total']-tb['total'] in [0,18],(ta,tb)
    return dict(total_delta=ta['total']-tb['total'],functions=changes)
def compare(raw,plan,records):
    results=[];old=ROOT/'.work'/OLD
    for case in plan['cases']:
        index=case['item']['index'];item=case['item'];prior=case['prior'];previous=read(ROOT/case['previous'])
        base=raw/'adopted';new=old if index==0 else raw/'candidate'
        a,=[r for r in records if r['mode']=='adopted' and r['index']==index]
        c=plan['retained_record'] if index==0 else next(r for r in records if r['mode']=='candidate' and r['index']==index)
        sp=read(base/f'{index}-profile.json');cp=read(new/f'{index}-profile.json');ss=stats(base,index)
        for k in ['peak_guest_memory','entropy_calls','entropy_bytes']:assert ss[k]==prior['statistics'][k]
        historic=drift(sp,previous)
        # The current adopted profile, not a tolerance, is the new exact control.
        admitted=validate_case(base,a,item,dict(statistics=ss),sp)
        candidate=validate_case(new,c,item,dict(statistics=ss),sp)
        results.append(dict(index=index,name=item['name'],adopted=admitted,candidate=candidate,historical_drift=historic))
    return results

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        old=ROOT/'.work'/OLD;outer=ROOT/'.work/experiments'/OLD;op=read(old/'plan.json');rows=read(old/'records.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==terminal['cwd']==str(ROOT)
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert "AssertionError: (0, 'instructions')" in (outer/'command.log').read_text()
        assert len(rows)==1 and rows[0]['index']==0 and rows[0]['returncode']==0
        for stream in ['stdout','stderr']:assert sha(old/f'0.{stream}')==rows[0][stream+'_sha256']
        frozen=dict(op['frozen'])
        for path,h in frozen.items():assert sha(ROOT/path)==h,path
        adopted=ROOT/'.work/interpreter-tools'/KEY/'rust-interp-vm';assert sha(adopted)==VM_HASH
        paths=[adopted,*old.rglob('*'),outer/'plan.json',outer/'status.json',outer/'command.log',
               *Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]
        for p in paths:
            if p.is_file():assert not p.is_symlink();frozen[str(p.relative_to(ROOT))]=sha(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        for mode in ['adopted','candidate']:(raw/mode).mkdir()
        plan=dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=op['cases'],retained_record=rows[0],
            candidate_vm=op['vm'],adopted_vm=str(adopted),candidate_vm_sha256=op['vm_sha256'],adopted_vm_sha256=VM_HASH,
            library=op['library'],controller_command=[sys.executable,*sys.orig_argv[1:]],host_before=host(),
            expected_commands=5,reused_guest_commands=1,performance_measurement=False)
        assert all(q['returncode']==q['value']==0 and q['length']==4 for q in plan['host_before']['queries'])
        write(raw/'plan.json',plan);records=[];write(raw/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=plan['library'],RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        for case in plan['cases']:
            index=case['item']['index'];item=case['item']
            for mode in (['adopted'] if index==0 else ['adopted','candidate']):
                require_space(ROOT,8);directory=raw/mode;vm=plan[mode+'_vm'];assert sha(Path(vm))==plan[mode+'_vm_sha256']
                command=[vm,'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                    '--jit-code-dump',str(directory/f'{index}-code'),'--jit-operation-map','--profile',str(directory/f'{index}-profile.json'),
                    '--profile-test',item['name'],'--suite-catalog',str(ROOT/item['catalog']),
                    '--instruction-limit',str(item['limits']['instructions']),'--allocation-limit',str(item['limits']['allocations']),str(ROOT/item['artifact'])]
                child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(ROOT/case['tape'])),
                    receipt_path=raw/'active.json',receipt=dict(index=index,mode=mode))
                for stream,value in [('stdout',out),('stderr',err)]:(directory/f'{index}.{stream}').write_text(value)
                records.append(dict(index=index,mode=mode,command=command,pid=child.pid,returncode=child.returncode,
                    stdout_sha256=sha(directory/f'{index}.stdout'),stderr_sha256=sha(directory/f'{index}.stderr')))
                write(raw/'records.json',records);assert child.returncode==0,(out+err)[-4000:]
            # Fail before starting another original case if this pair differs.
            partial=dict(plan,cases=[case]);comparison=compare(raw,partial,records)[0]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(index,'exact current-host A/B passed; historical delta',comparison['historical_drift']['total_delta'],flush=True)
        end=host();assert end==plan['host_before'];write(raw/'host-after.json',end)
        comparisons=compare(raw,plan,records);result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=5,reused_guest_commands=1,
            comparisons=comparisons,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
            exact_current_per_pc_counts=True,exact_memory_and_entropy=True,exact_operation_maps=True,
            historical_attempt_preserved=OLD,adopted_tool_key=KEY,vm_sha256=plan['candidate_vm_sha256'],
            performance_measurement=False,default_runtime_adoption=False))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        assert len(records)==summary['commands']==plan['expected_commands']==5 and summary['status']=='passed'
        for row in records:
            assert row['command'][0]==plan[row['mode']+'_vm']
            for stream in ['stdout','stderr']:assert sha(raw/row['mode']/f"{row['index']}.{stream}")==row[stream+'_sha256']
        assert read(raw/'host-after.json')==plan['host_before']
        assert compare(raw,plan,records)==summary['comparisons']
        bindings={}
        for path,h in plan['frozen'].items():
            assert sha(ROOT/path)==h,path
            if not path.startswith(('.work/','results/')):
                assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)).hexdigest()==h
            bindings[path]=dict(sha256=h,revision=plan['source_revision'])
        evidence={}
        for p in [*raw.rglob('*'),outer/'plan.json',outer/'status.json',outer/'command.log']:
            if p.is_file():assert not p.is_symlink();evidence[str(p.relative_to(ROOT))]=sha(p)
        assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_semantic_comparisons_recomputed=True,
            historical_failure_preserved=True,frozen_inputs=len(bindings),evidence_files=len(evidence),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
        failure=ROOT/'results'/OLD;failure.mkdir(exist_ok=False)
        t=ROOT/'.work/experiments'/OLD/'status.json';(failure/'terminal.json').write_bytes(t.read_bytes())
        write(failure/'summary.json',dict(status='failed',source_revision=read(ROOT/'.work'/OLD/'plan.json')['source_revision'],
            raw='.work/'+OLD,commands=1,original_assertions_passed=True,failed_check='historical instructions mismatch',
            historical_instructions=15849531246,current_instructions=15849531264,
            continuation=RUN,retained_original_profile=True,performance_measurement=False))
        write(failure/'closure.json',dict(status='closed',all_hashes_verified=True,expected_returncode=1,
            summary_sha256=sha(failure/'summary.json'),terminal_sha256=sha(failure/'terminal.json'),
            continuation_closure_sha256=sha(out/'closure.json'),continuation_closure=str((out/'closure.json').relative_to(ROOT))))
        print('Closed exact current-host profiles and preserved historical failure; no new guest execution')
if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()

"""Validate heap metadata on original suites and exact adopted native code."""
import ctypes,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from native_observation import validate,exact_logical_counts
import native_observation
RUN='heap-layout-profile-03'
RETAINED=ROOT/'.work/heap-layout-profile-02'
COMPARISON=ROOT/'benchmarks/experiments/heap-layout-native-comparison'
sys.path.insert(0,str(COMPARISON))
from compare import compare as compare_native
spec=importlib.util.spec_from_file_location('qualified_relocation',COMPARISON/'qualify.py')
relocation=importlib.util.module_from_spec(spec);spec.loader.exec_module(relocation)
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())

def host():
    lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True);query=lib.sysctlbyname
    query.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t];query.restype=ctypes.c_int
    rows=[]
    for name in ['hw.optional.arm.FEAT_FAMINMAX','hw.optional.arm.FEAT_LUT']:
        value=ctypes.c_uint32(0);length=ctypes.c_size_t(4);ctypes.set_errno(0)
        rc=query(name.encode(),ctypes.byref(value),ctypes.byref(length),None,0)
        rows.append(dict(name=name,returncode=rc,errno=ctypes.get_errno(),value=value.value,length=length.value))
    return dict(sw_vers=subprocess.check_output(['/usr/bin/sw_vers'],text=True),uname=list(os.uname()),queries=rows)

def validate_case(raw,row,item,prior,previous):
    index=item['index'];profile_path=raw/f'{index}-profile.json';dump_path=raw/f'{index}-code'
    out=(raw/f'{index}.stdout').read_text();err=(raw/f'{index}.stderr').read_text()
    assert row['returncode']==0 and out=='0\n'
    selected,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
    for key in ['name','artifact_sha256','catalog_sha256']:assert selected[key]==item[key]
    stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
    for key in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']:
        assert stats[key]==prior['statistics'][key],(index,key)
    profile=read(profile_path);totals=exact_logical_counts(profile,previous)
    assert totals['total']==stats['instructions'] and totals['native']==stats['jit_instructions']
    code=(dump_path/'code.bin').read_bytes();mapping=read(dump_path/'operations.json');regions=read(dump_path/'map.json')
    observed=validate(mapping,regions,code,profile,row['pid'])
    adopted=ROOT/'.work/compact-switch-current-host-01/adopted'/f'{index}-code'
    oldcode=(adopted/'code.bin').read_bytes();oldmap=read(adopted/'operations.json');oldregions=read(adopted/'map.json')
    oldrows=read(adopted.parent.parent/'records.json')
    oldrow,=[r for r in oldrows if r['index']==index and r['mode']=='adopted']
    validate(oldmap,oldregions,oldcode,previous,oldrow['pid'])
    equality=compare_native((oldcode,oldmap,oldregions,previous),(code,mapping,regions,profile))
    return dict(index=index,statistics=stats,logical_counts=totals,native_code_bytes=len(code),mapped_spans=observed['spans'],relocation_equality=equality,
        profile_sha256=sha(profile_path),code_sha256=sha(dump_path/'code.bin'),
        operations_sha256=sha(dump_path/'operations.json'),regions_sha256=sha(dump_path/'map.json'))

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        def closed(name):
            out=ROOT/'results'/name;c=bind(out/'closure.json')
            assert c['status']=='closed' and c['all_hashes_verified']
            s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
            assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            return s
        qualified=closed('heap-layout-native-comparison-01')
        assert qualified['tests']==9 and qualified['original_project_guest_commands']==0 and qualified['reused_guest_commands']==1
        qplan=bind(ROOT/qualified['raw']/'plan.json',qualified['plan_sha256'])
        for p,h in qplan['frozen'].items():bind(ROOT/p,h)
        for p,h in qualified['outputs'].items():bind(ROOT/p,h)
        assert relocation.saved_block()[0]==qualified['proof']
        retained_plan=read(RETAINED/'plan.json');retained_row,=read(RETAINED/'records.json')
        assert retained_row['index']==0 and retained_row['returncode']==0
        build=closed('heap-layout-workspace-02')
        assert build['tests']['debug']==build['tests']['release']==dict(passed=618,ignored=13)
        assert build['tests']['python']==dict(discovered=468,passed=446,skipped=22)
        build_plan=bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        for path,h in build_plan['frozen'].items():
            if path.startswith(('crates/','scripts/','tests/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/path,h)
        assert len(build['outputs'])==1
        vm_path,vm_hash=next(iter(build['outputs'].items()));vm=ROOT/vm_path;bind(vm,vm_hash)
        baseline=closed('compact-switch-current-host-01')
        assert baseline['adopted_tool_key']==BASELINE and baseline['exact_current_per_pc_counts']
        old=ROOT/baseline['raw'];old_plan=bind(old/'plan.json',baseline['plan_sha256'])
        bind(old/'records.json',baseline['records_sha256'])
        observer=closed('scratch-memory-values-profile-01')
        observer_raw=ROOT/observer['raw']
        observer_plan=bind(observer_raw/'plan.json',observer['plan_sha256'])
        controls=bind(observer_raw/'controls.json',observer['controls_sha256']);assert controls['returncode']==0
        for stream in ['stdout','stderr']:bind(observer_raw/('controls.'+stream),controls[stream+'_sha256'])
        assert 'Ran 3 tests' in (observer_raw/'controls.stderr').read_text()
        model=Path(native_observation.__file__)
        bind(model,observer_plan['frozen'][str(model.relative_to(ROOT))])
        library=Path(old_plan['library']);bind(library,old_plan['frozen'][str(library.relative_to(ROOT))])
        host_before=host();assert host_before==old_plan['host_before']==retained_plan['host_before'],'host changed before guest admission'
        assert retained_plan['vm_sha256']==vm_hash
        cases=[]
        for old_case in old_plan['cases']:
            item=old_case['item'];index=item['index']
            control,=[r for r in baseline['comparisons'] if r['index']==index]
            assert item['name']==control['name']
            prior=control['adopted'];previous=old/'adopted'/f'{index}-profile.json'
            bind(previous,prior['profile_sha256']);tape=ROOT/old_case['tape']
            for filename,key in [('code.bin','code_sha256'),('operations.json','operations_sha256'),('map.json','regions_sha256')]:
                bind(old/'adopted'/f'{index}-code'/filename,prior[key])
            bind(tape,old_plan['frozen'][old_case['tape']])
            for key in ['artifact','catalog']:bind(ROOT/item[key],item[key+'_sha256'])
            cases.append(dict(item=item,prior=prior,previous=str(previous.relative_to(ROOT)),tape=str(tape.relative_to(ROOT))))
        assert [c['item']['index'] for c in cases]==[0,1,2]
        assert [c['prior']['statistics']['instructions'] for c in cases]==[15849531264,13363262210,4291122869]
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=cases,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=2,retained_record=retained_row,reused_guest_commands=1,vm=str(vm),vm_sha256=vm_hash,
            library=str(library),reused_model_controls=3,host_before=host_before,adopted_tool_key=BASELINE,
            cargo_features=build['cargo_features'],performance_measurement=False,original_project_guest_commands=2))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        records=[];comparisons=[validate_case(RETAINED,retained_row,cases[0]['item'],cases[0]['prior'],read(ROOT/cases[0]['previous']))];write(raw/'records.json',records)
        for case in cases[1:]:
            require_space(ROOT,8);item=case['item'];index=item['index'];assert sha(vm)==vm_hash
            command=[str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                '--jit-code-dump',str(raw/f'{index}-code'),'--jit-operation-map','--profile',str(raw/f'{index}-profile.json'),
                '--profile-test',item['name'],'--suite-catalog',str(ROOT/item['catalog']),
                '--instruction-limit',str(item['limits']['instructions']),'--allocation-limit',str(item['limits']['allocations']),str(ROOT/item['artifact'])]
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(ROOT/case['tape'])),
                receipt_path=raw/'active.json',receipt=dict(index=index))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/f'{index}.{stream}').write_text(value)
            row=dict(index=index,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(raw/f'{index}.stdout'),stderr_sha256=sha(raw/f'{index}.stderr'))
            records.append(row);write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-4000:]
            comparisons.append(validate_case(raw,row,item,case['prior'],read(ROOT/case['previous'])))
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(index,'original assertions, exact logical counts, memory, entropy and native maps passed',flush=True)
        assert host()==host_before;write(raw/'host-after.json',host_before)
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=2,reused_guest_commands=1,
            comparisons=comparisons,vm_sha256=vm_hash,reused_model_controls=3,original_project_guest_commands=2,
            adopted_tool_key=BASELINE,cargo_features=build['cargo_features'],
            exact_per_pc_counts=True,exact_memory_and_entropy=True,exact_operation_maps=True,exact_native_code_modulo_scalar_entry_addresses=True,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),performance_measurement=False,default_runtime_adoption=False))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        assert len(records)==summary['commands']==plan['expected_commands']==2 and summary['status']=='passed'
        assert read(raw/'host-after.json')==plan['host_before']
        case=plan['cases'][0]
        comparisons=[validate_case(RETAINED,plan['retained_record'],case['item'],case['prior'],read(ROOT/case['previous']))]
        for row,case in zip(records,plan['cases'][1:]):
            assert row['index']==case['item']['index'] and row['command'][0]==plan['vm']
            for stream in ['stdout','stderr']:assert sha(raw/f"{row['index']}.{stream}")==row[stream+'_sha256']
            comparisons.append(validate_case(raw,row,case['item'],case['prior'],read(ROOT/case['previous'])))
        assert comparisons==summary['comparisons'] and sha(Path(plan['vm']))==summary['vm_sha256']==plan['vm_sha256']
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
            frozen_inputs=len(bindings),evidence_files=len(evidence),summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
        print('Closed all three original profiles: retained block plus two new guests; exact proven scalar relocations')
if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()

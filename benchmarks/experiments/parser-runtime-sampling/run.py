"""One fresh original parser sample on the adopted custom runtime."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-runtime-sampling'))
from attribute import attribute
NAME='parser-runtime-sampling-02'
SAMPLE='parser-runtime-sample-01'
KEY='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
VM='6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'
def read(p):return json.loads(p.read_text())
def main():
    lock=(ROOT/'.work/benchmark.lock').open('a');acquire_lock(lock,45);require_space(ROOT,12)
    frozen={}
    def bind(p,h=None):
        p=Path(p);actual=sha(p)
        if h is not None:assert actual==h,str(p)
        frozen[str(p.relative_to(ROOT))]=actual
        return read(p) if p.suffix=='.json' else actual
    tool,_=installed_tools(KEY);bind(tool/'rust-interp-vm',VM)
    adopted=ROOT/'results/scratch-scalar-main-qualification-01'
    closed=bind(adopted/'closure.json');q=bind(adopted/'summary.json',closed['summary_sha256'])
    assert closed['status']=='closed' and q['status']=='passed' and q['tool_key']==KEY and q['binaries']['rust-interp-vm']==VM
    profile_dir=ROOT/'results/conditional-demand-parser-profile-01'
    pc=bind(profile_dir/'closure.json');ps=bind(profile_dir/'summary.json',pc['summary_sha256'])
    assert pc['status']=='closed' and ps['status']=='passed'
    row,=[r for r in ps['comparisons'] if r['mode']=='control'];assert row['tool_key']==KEY
    declines=row['statistics']['jit_declined_functions'];assert declines==1
    profile,digest=next((ROOT/p,h) for p,h in row['evidence'].items() if p.endswith('/control-profile.json'))
    bind(profile,digest)
    artifact=ROOT/'.work/guarded-local-facts-main-parser-01/artifact.rbc';ah=bind(artifact,'a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61')
    catalog=ROOT/'.work/guarded-local-facts-main-parser-01/entry_catalog.json';c=bind(catalog,'ccfc22456d1ed03a43741a052c9b06ce59517afd4856dffa88bb76f2c4fadd8b')
    assert c['artifact_sha256']==ah and len([r for r in c['entries'] if r['name']==ps['test']])==1
    previous=ROOT/'.work/scalar-runtime-sampling-01'
    plan=bind(previous/'plan.json');rows=bind(previous/'records.json')
    control,=[r for r in rows if r['label']=='controls'];assert control['returncode']==0
    bind(previous/'controls.stderr',control['stderr_sha256']);assert 'Ran 9 tests' in (previous/'controls.stderr').read_text()
    for p,h in plan['frozen'].items():
        if p in ['scripts/summarize_owned_sample.py','scripts/compare_saved_runtime.py'] or p.startswith(('benchmarks/experiments/scalar-runtime-sampling/',
            'benchmarks/experiments/scalar-private-transfers/native_observation.py',
            'benchmarks/experiments/scalar-private-transfers/test_native_observation.py','benchmarks/experiments/operation-map/')):bind(ROOT/p,h)
    for p in ['scripts/interpreter.py','scripts/sample_owned_vm.py','scripts/workflow_io.py','scripts/supervise_experiment.py']:bind(ROOT/p)
    for p in Path(__file__).parent.iterdir():
        if p.suffix in ['.py','.md']:bind(p)
    for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock'],text=True).splitlines():bind(ROOT/p)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
    work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
    write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        frozen=frozen,tool_key=KEY,vm_sha256=VM,guest_commands=1,expected_child_commands=2,reused_controls=9,
        initial_gib=12,minimum_child_gib=8,sample_seconds=1,expected_jit_declines=declines,performance_measurement=False))
    records=[];write(work/'records.json',records)
    env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
    assert not any(k.startswith('DYLD_') for k in env);env['PYTHONDONTWRITEBYTECODE']='1'
    def execute(label,command):
        assert all(sha(ROOT/p)==h for p,h in frozen.items());require_space(ROOT,8)
        child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
        for stream,payload in [('stdout',out),('stderr',err)]:(work/(label+'.'+stream)).write_text(payload)
        records.append(dict(label=label,pid=child.pid,command=command,returncode=child.returncode,
            stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
        write(work/'records.json',records);assert child.returncode==0,(out+err)[-4000:]
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
    lock.close()
    execute('parser-sample',[sys.executable,'scripts/sample_owned_vm.py','--tool-key',KEY,'--artifact',str(artifact),
        '--artifact-sha256',ah,'--run-id',SAMPLE,'--repetitions','1','--duration','1',
        '--instruction-limit','100000000000','--allocation-limit','150000','--jit-persistent-registers',
        '--jit-resumable-calls','--jit-scalar-calls','--dump-code','--jit-operation-map',
        '--select-test',ps['test'],'--suite-catalog',str(catalog),'--lock-wait-seconds','45',
        '--expected-jit-declines',str(declines),'--minimum-free-bytes',str(8*1024**3)])
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        execute('parser-summary',[sys.executable,'scripts/summarize_owned_sample.py','--run-id',SAMPLE])
        report=dict(case='parser',run_id=SAMPLE,**attribute(SAMPLE,profile,VM))
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',tool_key=KEY,vm_sha256=VM,guest_commands=1,commands=2,
            reused_controls=9,cases=[report],raw=str(work.relative_to(ROOT)),all_frozen_inputs_verified=True,
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            performance_measurement=False,profile_used_for_static_identity_only=True))
if __name__=='__main__':main()

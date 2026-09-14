"""One exact original parser replay with bounded interpreted switch indices."""
import json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
sys.path.insert(0,str(ROOT/'benchmarks/experiments/indexed-switch-workflows'))
from native_observation import validate,exact_logical_counts
from relocation import compare as compare_code
NAME='indexed-switches-parser-profile-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            p=Path(p);digest=sha(p)
            if h is not None:assert digest==h,str(p)
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        def closed(name):
            folder=ROOT/'results'/name;c=bind(folder/'closure.json');assert c['status']=='closed'
            s=bind(folder/'summary.json',c['summary_sha256']);assert s['status']=='passed'
            return s
        build=closed('indexed-switches-build-02');strict=closed('indexed-switches-qualification-01');small=closed('indexed-switches-profile-02')
        assert build['composition']['kind']=='indexed-switches' and build['tests']['test-debug']==build['tests']['test-release']>=612
        assert strict['commands']==122 and strict['source_restored'] and strict['indexed_partial_artifact_rejections']==1
        assert small['exact_per_pc_counts'] and small['exact_operation_map_reconstruction']
        assert build['tool_key']==strict['tool_key']==small['tool_key']
        tool,key=installed_tools(build['tool_key'])
        for p,h in build['binaries'].items():bind(tool/p,h)
        prior=closed('conditional-demand-parser-profile-01')
        reference,=[r for r in prior['comparisons'] if r['mode']=='control']
        assert reference['tool_key']==build['matched_control']['tool_key']
        for p,h in reference['evidence'].items():bind(ROOT/p,h)
        profile_path,=[ROOT/p for p in reference['evidence'] if p.endswith('/control-profile.json')]
        code_path,=[ROOT/p for p in reference['evidence'] if p.endswith('/code.bin')]
        previous=read(profile_path)
        tape=ROOT/'.work/conditional-demand-parser-profile-01/entropy.tape';bind(tape,prior['entropy_tape_sha256'])
        artifact=ROOT/'.work/guarded-local-facts-main-parser-01/artifact.rbc';ah=bind(artifact,'a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61')
        catalog=ROOT/'.work/guarded-local-facts-main-parser-01/entry_catalog.json';bind(catalog,'ccfc22456d1ed03a43741a052c9b06ce59517afd4856dffa88bb76f2c4fadd8b')
        entropy=bind(ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json');assert entropy['status']=='passed'
        library=ROOT/entropy['library'];bind(library,entropy['library_sha256'])
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        for p in ['scripts/workflow_io.py','scripts/compare_saved_runtime.py','scripts/interpreter.py',
            'benchmarks/experiments/indexed-switch-workflows/native_observation.py',
            'benchmarks/experiments/indexed-switch-workflows/relocation.py']:bind(ROOT/p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_commands=1,tool_key=key,minimum_child_gib=8,performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_ENTROPY_TAPE=str(tape),RUST_INTERP_ENTROPY_MODE='replay',RUST_INTERP_VM_STATS='1')
        current=work/'candidate-profile.json';dump=work/'candidate-code'
        command=list(map(str,[tool/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
            '--jit-scalar-calls','--indexed-switches','--instruction-limit','100000000000','--allocation-limit','150000',
            '--profile',current,'--profile-test',prior['test'],'--suite-catalog',catalog,'--jit-code-dump',dump,'--jit-operation-map',artifact]))
        require_space(ROOT,8);child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label='candidate'))
        records=[dict(label='candidate',command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err)]
        write(work/'records.json',records);assert child.returncode==0 and out=='0\n',err
        selection,=[json.loads(s.split(': ',1)[1]) for s in err.splitlines() if s.startswith('rust-interp-profile-selection: ')]
        assert selection['name']==prior['test'] and selection['artifact_sha256']==ah and selection['catalog_sha256']==sha(catalog)
        stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
        for n in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes','jit_bytes','jit_instructions','jit_declined_functions']:
            assert stats[n]==reference['statistics'][n],n
        profile=read(current);counts=exact_logical_counts(profile,previous);assert counts==reference['logical_counts']
        code=(dump/'code.bin').read_bytes()
        native_equality=compare_code(code_path.read_bytes(),read(code_path.with_name('map.json')),
            read(code_path.with_name('operations.json')),previous,code,read(dump/'map.json'),read(dump/'operations.json'),profile)
        validate(read(dump/'operations.json'),read(dump/'map.json'),code,profile,child.pid)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        evidence={str(p.relative_to(ROOT)):sha(p) for p in [current,*dump.iterdir()] if p.is_file()}
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=1,tool_key=key,matched_control_key=reference['tool_key'],
            test=prior['test'],indexed_switches=True,exact_per_pc_counts_memory_entropy=True,exact_native_bytes_after_bound_relocation=True,native_equality=native_equality,
            exact_operation_map_reconstruction=True,comparisons=[dict(mode='candidate',statistics=stats,logical_counts=counts,evidence=evidence)],
            entropy_tape_path=str(tape.relative_to(ROOT)),entropy_tape_sha256=sha(tape),raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),performance_measurement=False))
if __name__=='__main__':main()

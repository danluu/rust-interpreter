"""Compare exact current parser work under eager and reached-region emission."""
import hashlib, importlib.util, json, os, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write
NAME = 'demand-large-function-profile-01'
BASELINE = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
TEST = 'tests_dump::c_reference_vectors'

def read(path): return json.loads(path.read_text())

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 12)
        directory = Path(__file__).parent
        build_path = ROOT / 'results/demand-region-build-02/summary.json'; build = read(build_path)
        assert build['status'] == 'passed' and build['composition']['kind'] == 'demand-region'
        assert build['tests'] == {'test-debug': 637, 'test-release': 637}
        candidate, key = installed_tools(build['tool_key']); baseline, _ = installed_tools(BASELINE)
        assert build['matched_control']['tool_key'] == BASELINE
        for name, digest in build['binaries'].items(): assert sha(candidate/name) == digest
        for name, digest in build['matched_control']['binaries'].items(): assert sha(baseline/name) == digest
        proof_path = ROOT / 'results/guarded-local-facts-main-parser-01/summary.json'; proof = read(proof_path)
        assert proof['status'] == 'passed' and proof['custom_tests_passed'] == 114 and proof['source_unchanged']
        artifact, catalog = [ROOT / proof['artifacts'][name]['path'] for name in ['artifact', 'entry_catalog']]
        for name, path in [('artifact', artifact), ('entry_catalog', catalog)]: assert sha(path) == proof['artifacts'][name]['sha256']
        assert sha(artifact) == 'a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61'
        assert read(catalog)['artifact_sha256'] == sha(artifact)
        entry, = [e for e in read(catalog)['entries'] if e['name'] == TEST]; assert entry['function'] == 113
        entropy_path = ROOT / 'results/fixed-frame-clear-entropy-check-01/summary.json'; entropy = read(entropy_path)
        assert entropy['status'] == 'passed'; library = ROOT / entropy['library']; assert sha(library) == entropy['library_sha256']
        eager_path = ROOT / 'benchmarks/experiments/native-continuation-snapshot-workflows/native_observation.py'
        demand_path = ROOT / 'benchmarks/experiments/demand-region-workflows/native_observation.py'
        eager = module('eager_observation', eager_path); demand = module('demand_observation', demand_path)
        profile_proof_path = ROOT / 'results/demand-region-profile-01/summary.json'; profile_proof = read(profile_proof_path)
        assert profile_proof['status'] == 'passed' and profile_proof['tool_key'] == key and profile_proof['python_controls'] == 4
        original_plan = ROOT / profile_proof['raw'] / 'plan.json'; assert sha(original_plan) == profile_proof['plan_sha256']
        assert read(original_plan)['frozen'][str(demand_path.relative_to(ROOT))] == sha(demand_path)
        old_path = ROOT / 'results/scratch-memory-values-profile-01/summary.json'; old = read(old_path)
        old_plan = ROOT / old['raw'] / 'plan.json'; assert sha(old_plan) == old['plan_sha256']
        assert read(old_plan)['frozen']['benchmarks/experiments/scratch-memory-values/native_observation.py'] == sha(eager_path)
        paths = [build_path, proof_path, artifact, catalog, entropy_path, library, eager_path, demand_path,
            profile_proof_path, original_plan, old_path, old_plan]
        paths += [candidate/n for n in build['binaries']] + [baseline/n for n in build['binaries']]
        paths += [p for p in directory.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','interpreter.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work = ROOT / '.work' / NAME; work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,expected_commands=3,tool_key=key,matched_control_key=BASELINE,test=TEST,
            admission_gib=12,minimum_child_gib=8,performance_measurement=False,fresh_owner=True))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_VM_STATS='1',RUST_INTERP_ENTROPY_TAPE=str(work/'entropy.tape'))
        records=[]; comparisons=[]; previous=None; reference_stats=None
        for label, tools, entropy_mode in [('record',baseline,'record'),('control',baseline,'replay'),('candidate',candidate,'replay')]:
            require_space(ROOT,8)
            profile_path=work/(label+'-profile.json'); dump=work/(label+'-code')
            command=[tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls']
            if label=='candidate': command+=['--jit-demand-regions']
            command+=['--instruction-limit','100000000000','--allocation-limit','150000','--profile',profile_path,
                '--profile-test',TEST,'--suite-catalog',catalog,'--jit-code-dump',dump,'--jit-operation-map',artifact]
            command=list(map(str,command))
            child,out,err=capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_MODE=entropy_mode),
                receipt_path=work/'active.json',receipt=dict(label=label))
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,stdout=out,stderr=err))
            write(work/'records.json',records); assert child.returncode==0 and out=='0\n',err
            selection,=[json.loads(line.split(': ',1)[1]) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
            assert selection['name']==TEST and selection['function']==113
            assert selection['artifact_sha256']==sha(artifact) and selection['catalog_sha256']==sha(catalog)
            stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            assert profile_path.stat().st_size<=256*1024**2
            profile=read(profile_path)
            if previous is None: previous=profile; reference_stats=stats
            totals=demand.exact_logical_counts(profile,previous)
            assert totals['total']==stats['instructions'] and totals['native']==stats['jit_instructions']
            for name in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']: assert stats[name]==reference_stats[name],(label,name)
            mapping=read(dump/'operations.json'); ranges=read(dump/'map.json'); code=(dump/'code.bin').read_bytes()
            observed=(demand if label=='candidate' else eager).validate(mapping,ranges,code,profile,child.pid)
            logical,_=demand.logical_counts(profile)
            functions=[]
            for fid,f in enumerate(profile['functions']):
                total=sum(logical[fid]); interpreted=sum(f['interpreted'])
                if not total: continue
                emitted=[r for r in ranges['ranges'] if r['function']==fid]
                functions.append(dict(function=fid,name=f['name'],operations=len(f['operations']),logical=total,
                    interpreted=interpreted,native=total-interpreted,code_bytes=sum(r['end']-r['offset'] for r in emitted),regions=len(emitted)))
            if label=='candidate':
                for name in ['jit_demand_plan_bytes','jit_demand_metadata_bytes']: assert 0<stats[name]<=16*1024**2
            evidence={str(path.relative_to(ROOT)):sha(path) for path in [profile_path,dump/'code.bin',dump/'map.json',dump/'operations.json']}
            comparisons.append(dict(mode=label,tool_key=key if label=='candidate' else BASELINE,statistics=stats,
                logical_counts=totals,large_functions=[f for f in functions if f['operations']>65536],
                most_interpreted=sorted(functions,key=lambda f:-f['interpreted'])[:12],mapped_spans=observed['spans'],evidence=evidence))
            assert all(sha(ROOT/p)==h for p,h in frozen.items())
            print(label,'original counts/memory/entropy/code PASS',flush=True)
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=3,test=TEST,tool_key=key,matched_control_key=BASELINE,
            comparisons=comparisons,exact_per_pc_counts_memory_entropy=True,exact_operation_map_reconstruction=True,
            entropy_tape_sha256=sha(work/'entropy.tape'),raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            records_sha256=sha(work/'records.json'),performance_measurement=False,fresh_owner=True))

if __name__=='__main__': main()

"""Weight register-storage sizes by exact saved direct calls; execute no guest."""
import importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
NAME='large-register-calls-01'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        helper=ROOT/'benchmarks/experiments/native-continuation-snapshot-workflows/native_observation.py'
        spec=importlib.util.spec_from_file_location('observation',helper);observer=importlib.util.module_from_spec(spec);spec.loader.exec_module(observer)
        paths=[helper];cases=[]
        for name in ['scratch-memory-values-profile-01','conditional-demand-parser-profile-01']:
            folder=ROOT/'results'/name;summary=read(folder/'summary.json');closed=read(folder/'closure.json')
            assert summary['status']=='passed' and closed['status']=='closed' and closed['all_hashes_verified']
            assert sha(folder/'summary.json')==closed['summary_sha256'];paths += [folder/'summary.json',folder/'closure.json']
            if name=='scratch-memory-values-profile-01':
                assert summary['tool_key']=='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
                for row in summary['comparisons']:
                    if row['mode']!='candidate':continue
                    p=ROOT/row['profile_path'];assert sha(p)==row['profile_sha256'];cases.append((row['name'],p));paths.append(p)
            else:
                row,=[r for r in summary['comparisons'] if r['mode']=='control']
                assert row['tool_key']=='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
                item,=[(ROOT/p,h) for p,h in row['evidence'].items() if p.endswith('/control-profile.json')]
                p,digest=item;assert sha(p)==digest;cases.append((summary['test'],p));paths.append(p)
        assert len(cases)==4
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += [ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py']]
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,source_edits=0,minimum_free_gib=8,performance_measurement=False))
        results=[]
        for label,path in cases:
            profile=read(path);counts,totals=observer.logical_counts(profile);functions=profile['functions']
            calls=[0]*len(functions);scalar=[0]*len(functions);indirect=0
            for fid,f in enumerate(functions):
                for pc,op in enumerate(f['operations']):
                    if op.startswith('Call {'):
                        matched=re.match(r'^Call \{ function: (\d+), ',op);assert matched,op
                        target=int(matched[1]);assert target<len(functions);calls[target]+=counts[fid][pc]
                    elif op.startswith('CallIndirect {'):indirect+=counts[fid][pc]
                    elif op=='Return':scalar[fid]+=f.get('jit_scalar_hits',[0]*len(f['operations']))[pc]
            rows=[]
            for fid,f in enumerate(functions):
                if not calls[fid]:continue
                ordinary=max(0,calls[fid]-scalar[fid])
                rows.append(dict(function=fid,name=f['name'],registers=f['registers'],operations=len(f['operations']),
                    frame_bytes=f['frame_size'],direct_calls=calls[fid],scalar_returns=scalar[fid],ordinary_direct_calls_lower_bound=ordinary,
                    nominal_register_bytes=ordinary*f['registers']*16,nominal_frame_bytes=ordinary*max(f['frame_size'],1)))
            rows.sort(key=lambda r:-r['nominal_register_bytes'])
            results.append(dict(name=label,profile_path=str(path.relative_to(ROOT)),profile_sha256=sha(path),logical_counts=totals,
                indirect_calls=indirect,ordinary_direct_calls=sum(r['ordinary_direct_calls_lower_bound'] for r in rows),
                nominal_register_bytes=sum(r['nominal_register_bytes'] for r in rows),nominal_frame_bytes=sum(r['nominal_frame_bytes'] for r in rows),
                top=rows[:20],over_register_bound=[r for r in rows if r['registers']>65536]))
            write(work/(str(len(results)-1)+'-calls.json'),rows)
            print(label,json.dumps(results[-1]['over_register_bound']),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',profiles=results,new_guest_commands=0,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),artifacts={str(p.relative_to(ROOT)):sha(p) for p in work.glob('*-calls.json')},performance_measurement=False,
            limits='Nominal direct-call byte weights, not measured clearing. Current initialization proof may already elide clears. Scalar completions are subtracted conservatively; indirect calls, entry allocation and TLS callbacks are not attributed.'))
if __name__=='__main__':main()

"""Inspect saved large Switch case order and interpreted counts; no guest runs."""
import ast,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
NAME='interpreted-switch-census-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8);frozen={}
        def bind(p,h=None):
            p=Path(p);digest=sha(p)
            if h is not None:assert digest==h,str(p)
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        folder=ROOT/'results/large-register-calls-01';closed=bind(folder/'closure.json')
        saved=bind(folder/'summary.json',closed['summary_sha256'])
        assert closed['status']=='closed' and saved['status']=='passed' and len(saved['profiles'])==4
        for p in [Path(__file__),Path(__file__).with_name('PLAN.md'),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:bind(p)
        for c in saved['profiles']:bind(ROOT/c['profile_path'],c['profile_sha256'])
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,minimum_child_gib=8,performance_measurement=False))
        results=[]
        for case in saved['profiles']:
            profile=read(ROOT/case['profile_path']);rows=[]
            for fid,f in enumerate(profile['functions']):
                for pc,op in enumerate(f['operations']):
                    if not op.startswith('Switch {'):continue
                    m=re.fullmatch(r'Switch \{ value: (\d+), cases: (\[.*\]), otherwise: (\d+) \}',op);assert m,op[:100]
                    assert re.fullmatch(r'[\[\](), 0-9]*',m[2]) and len(m[2])<8*1024**2
                    cases=ast.literal_eval(m[2]);assert all(type(v) is tuple and len(v)==2 and all(type(n) is int and n>=0 for n in v) for v in cases)
                    if len(cases)<32:continue
                    keys=[a for a,_ in cases];count=f['interpreted'][pc]
                    rows.append(dict(function=fid,name=f['name'],pc=pc,cases=len(cases),interpreted=count,
                        ordered=all(a<=b for a,b in zip(keys,keys[1:])),unique=len(set(keys))==len(keys),
                        contiguous=all(b==a+1 for a,b in zip(keys,keys[1:])),
                        maximum_key=str(max(keys)),linear_comparison_upper_bound=len(cases)*count))
            rows.sort(key=lambda r:-r['linear_comparison_upper_bound'])
            results.append(dict(name=case['name'],switches=len(rows),interpreted=sum(r['interpreted'] for r in rows),
                linear_comparison_upper_bound=sum(r['linear_comparison_upper_bound'] for r in rows),rows=rows))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',profiles=results,new_guest_commands=0,performance_measurement=False,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),
            limits='Case-order and saved interpreted counts only; linear comparisons are upper bounds, not measured comparisons or time.'))
        print([(r['switches'],r['interpreted'],r['linear_comparison_upper_bound']) for r in results],flush=True)
if __name__=='__main__':main()

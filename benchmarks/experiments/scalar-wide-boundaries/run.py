"""Partition the closed broad boundary census and report a bounded shape grid."""
import collections
import itertools
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
NAME='scalar-wide-boundaries-01'
ALLOWED={'Imm','Local','Load','Store','Copy','Binary','Unary','Cast','Select','Jump','Switch','Assert','Return','Trap','FillBytes','CopyDynamic'}
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else None
        for p in [*Path(__file__).parent.glob('*.py'),Path(__file__).with_name('PLAN.md'),
                  ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']:
            bind(p)
        old=ROOT/'results/scalar-next-boundaries-02'
        closure=bind(old/'closure.json');assert closure['status']=='closed' and closure['all_hashes_verified']
        prior=bind(old/'summary.json',closure['summary_sha256'])
        bind(old/'terminal.json',closure['terminal_sha256'])
        bindings=bind(ROOT/closure['bindings'],closure['bindings_sha256'])
        for p,v in bindings.items():
            if v['kind']=='retained':bind(ROOT/p,v['sha256'])
        plan=bind(ROOT/prior['raw']/'plan.json',prior['plan_sha256'])
        typed=bind(ROOT/'.work/current-call-shapes-01/census.json')
        shapes={r['function']:r for r in typed['rows']}
        assert len(shapes)==typed['functions'] and all(sum(f['operation_histogram'].values())==f['operations'] for f in shapes.values())
        broad={i for i,f in shapes.items() if 0<f['operations']<=512 and f['frame_size']<=8192 and f['registers']<=4096
               and all(a['size']<=16 for a in f['arguments']) and f['result']['size']<=256
               and not any(f['operation_histogram'].get(k,0) for k in ['Call','CallIndirect'])
               and (f['frame_size']>512 or f['registers']>512 or f['result']['size']>16)}
        assert broad==set(plan['candidates']['wider_results']) and len(broad)==157
        def mask(f):
            return '+'.join(k for k,yes in [('frame',f['frame_size']>512),('registers',f['registers']>512),('result',f['result']['size']>16)] if yes)
        partitions={m:{i for i in broad if mask(shapes[i])==m} for m in sorted({mask(shapes[i]) for i in broad})}
        assert set.union(*partitions.values())==broad and sum(map(len,partitions.values()))==len(broad)
        scalar_ops={i for i in broad if set(shapes[i]['operation_histogram'])<=ALLOWED}
        policies={'broad':broad,**{'partition/'+k:v for k,v in partitions.items()},'supported_opcode_families':scalar_ops}
        grid={}
        for frame,registers,result in itertools.product([512,1024,8192],[512,1024,4096],[32,64,128,256]):
            ids={i for i in scalar_ops if shapes[i]['frame_size']<=frame and shapes[i]['registers']<=registers and shapes[i]['result']['size']<=result}
            grid[frame,registers,result]=ids
            policies[f'grid/frame{frame}/registers{registers}/result{result}']=ids
        for a,ia in grid.items():
            for b,ib in grid.items():
                if all(x<=y for x,y in zip(a,b)):assert ia<=ib
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
              candidates={k:sorted(v) for k,v in policies.items()},guest_commands=0,performance_measurement=False))
        cases=[]
        for case in prior['cases']:
            old=case['policies']['wider_results'];targets=old['sampled_targets']
            assert len({t['function'] for t in targets})==len(targets) and {t['function'] for t in targets}<=broad
            reports={}
            for key,ids in policies.items():
                selected=[dict(t,registers=shapes[t['function']]['registers']) for t in targets if t['function'] in ids]
                parts=collections.Counter()
                for t in selected:
                    parts.update({'Call/'+k:v for k,v in t['call_parts'].items()})
                    parts.update({'Return/'+k:v for k,v in t['return_parts'].items()})
                reports[key]=dict(candidate_functions=len(ids),transition_samples=sum(parts.values()),
                    body_samples=sum(t['body_samples'] for t in selected),by_part=dict(parts),sampled_targets=selected)
            assert all(reports['broad'][k]==old[k] for k in ['candidate_functions','transition_samples','body_samples','by_part'])
            assert sum(reports['partition/'+k]['transition_samples'] for k in partitions)==old['transition_samples']
            assert sum(reports['partition/'+k]['body_samples'] for k in partitions)==old['body_samples']
            cases.append(dict(case=case['case'],generated_samples=case['generated_samples'],policies=reports))
            print(case['case'],{k:(v['candidate_functions'],v['transition_samples'],v['body_samples']) for k,v in reports.items()
                if k.startswith('partition/') or k in ['supported_opcode_families','grid/frame1024/registers512/result64']},flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',commands=1,cases=cases,raw=str(work.relative_to(ROOT)),
             plan_sha256=sha(work/'plan.json'),guest_commands=0,executable_code_publications=0,rust_builds=0,
             performance_measurement=False,grid_policies=len(grid),structural_partition_complete=True,
             scope='Exact partition of closed optimistic boundary coverage in adopted partial perturbed samples; no new memory, alias, CFG or native eligibility proof and no latency estimate.'))
if __name__=='__main__':main()

"""Join closed native frame-clear samples to original callee payload sizes."""
from bisect import bisect_right
from collections import Counter
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
NAME='frame-clear-sizes-01'
def read(p):return json.loads(p.read_text())
def locate(rows,starts,offset):
    i=bisect_right(starts,offset)-1
    assert i>=0 and rows[i]['offset']<=offset<rows[i]['end'] and offset%4==0
    return rows[i]
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8);frozen={}
        def bind(p,h=None):
            p=Path(p);digest=sha(p)
            if h is not None:assert digest==h,str(p)
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else digest
        folder=ROOT/'results/scalar-protocol-census-03';c=bind(folder/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        saved=bind(folder/'summary.json',c['summary_sha256']);assert saved['status']=='passed' and saved['guest_commands']==0
        bindings=bind(ROOT/c['bindings'],c['bindings_sha256'])
        for p,h in bindings['artifacts'].items():bind(ROOT/p,h)
        calls_dir=ROOT/'results/large-register-calls-01';cc=bind(calls_dir/'closure.json');assert cc['status']=='closed'
        calls=bind(calls_dir/'summary.json',cc['summary_sha256'])
        cases=[]
        for i,label in enumerate(['block','exhaustive']):
            capture=ROOT/'.work'/('scratch-scalar-runtime-sample-'+label+'-01')/'0'
            for p in [capture/'sample.txt',capture/'jit-code/operations.json']:
                original=bindings['source'][str(p.relative_to(ROOT))];bind(p,original['sha256'])
            profile=ROOT/calls['profiles'][i]['profile_path'];bind(profile,calls['profiles'][i]['profile_sha256'])
            cases.append((label,capture,profile))
        for p in [Path(__file__),Path(__file__).with_name('PLAN.md'),ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py',ROOT/'scripts/summarize_owned_sample.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,source_changes=0,minimum_child_gib=8,performance_measurement=False))
        results=[]
        for label,capture,profile in cases:
            fns=read(profile)['functions'];mapping=read(capture/'jit-code/operations.json')
            protocol=read(ROOT/saved['raw']/(label+'.json'));assert protocol['code_sha256']==mapping['code_sha256']
            spans=protocol['spans'];starts=[r['offset'] for r in spans]
            coarse=[dict(r,function=f['function']) for f in mapping['functions'] for r in f['spans'] if r['offset']<r['end']]
            positions=[r['offset'] for r in coarse];counts=Counter();clear=0;transitions=0
            for root in parse_tree((capture/'sample.txt').read_text()):
                for count,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                    rows=[locate(coarse,positions,a) for a in offsets]
                    assert len({(r['function'],r['pc'],r['kind']) for r in rows})==1
                    if rows[0]['kind']!='transition':continue
                    transitions+=count;fine=[locate(spans,starts,a) for a in offsets]
                    assert len({(r['function'],r['pc'],r['kind']) for r in fine})==1
                    row=fine[0]
                    if row['kind']!='call_frame_clear':continue
                    assert row['operation']=='Call';clear+=count
                    op=fns[row['function']]['operations'][row['pc']]
                    match=re.match(r'^Call \{ function: (\d+), ',op);assert match,op
                    callee=int(match[1]);counts[callee]+=count
            expected,=[r for r in saved['cases'] if r['case']==label]
            assert clear==expected['fine_samples']['Call/call_frame_clear'] and transitions==expected['transition_samples']
            rows=[dict(function=fid,name=fns[fid]['name'],frame_bytes=fns[fid]['frame_size'],samples=n)
                  for fid,n in counts.most_common()]
            results.append(dict(case=label,transition_samples=transitions,frame_clear_samples=clear,callees=rows,
                thresholds={str(size):sum(r['samples'] for r in rows if r['frame_bytes']>=size) for size in [256,512,1024,2048,4096]}))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',profiles=results,new_guest_commands=0,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),performance_measurement=False,limits='Exact saved self samples joined to static payload dimensions. Alignment padding is not attributed; no speedup or dynamic traffic estimate.'))
        print([(r['case'],r['thresholds']) for r in results],flush=True)
if __name__=='__main__':main()

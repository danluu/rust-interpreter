"""Count old bridge cursor traffic from closed profiles, without guest execution."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,12)
    proof_path=ROOT/'results/tree-bridge-profile-01/summary.json';proof=json.loads(proof_path.read_text())
    closure_path=ROOT/'results/tree-bridge-screen-token-01/closure.json';closure=json.loads(closure_path.read_text())
    assert proof['status']==closure['status']=='passed' and closure['parked']
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [proof_path,closure_path,Path(__file__)]}
    rows=[]
    for case in proof['comparisons']:
        path=ROOT/proof['raw']/f"{case['index']}-profile.json"
        assert sha(path)==case['profile_sha256'];evidence[str(path.relative_to(ROOT))]=sha(path)
        p=json.loads(path.read_text());stats=case['statistics'];regions=entries=instructions=leaf_entries=leaf_regions=0
        top=[]
        for fid,f in enumerate(p['functions']):
            hits=f['jit_tree_blocks'];ends=f['jit_tree_block_ends'];ops=f['operations']
            assert len(hits)==len(ends)==len(ops)
            count=sum(hits)
            if not count:continue
            assert all(type(h) is int and h>=0 and (not h or pc<ends[pc]<=len(ops)) for pc,h in enumerate(hits))
            regions+=count;entries+=hits[0];instructions+=sum(h*(ends[pc]-pc) for pc,h in enumerate(hits))
            leaf=not any(op.startswith('Call {') for op in ops)
            if leaf:leaf_entries+=hits[0];leaf_regions+=count
            top.append(dict(function=fid,name=f['name'],entries=hits[0],regions=count,leaf=leaf))
        assert entries==stats['jit_tree_entries']+stats['jit_tree_calls']
        assert instructions==stats['jit_tree_instructions']
        rows.append(dict(index=case['index'],name=case['name'],outer_bridges=stats['jit_tree_entries'],
            nested_calls=stats['jit_tree_calls'],tree_regions=regions,leaf_entries=leaf_entries,leaf_regions=leaf_regions,
            old_budget_load_store_instructions=2*regions,old_budget_all_instructions=4*regions,
            hottest_functions=sorted(top,key=lambda x:x['regions'],reverse=True)[:15]))
        del p
    assert all(sha(ROOT/p)==h for p,h in evidence.items())
    out=ROOT/'results/tree-bridge-cursor-census-01';out.mkdir(exist_ok=False)
    write(out/'summary.json',dict(status='passed',performance_measurement=False,guest_commands=0,evidence=evidence,cases=rows,
        scope='Counts from exact closed tree block profiles; two scalar budget memory operations and four total instructions emitted per region. Counts are not cycle savings or speedups.'))
    for row in rows:print(json.dumps({k:v for k,v in row.items() if k!='hottest_functions'}),flush=True)

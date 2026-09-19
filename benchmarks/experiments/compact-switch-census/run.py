import ast
from collections import Counter
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/composed-native-attribution'))
from composed_native_observation import validate,locate
RUN='compact-switch-census-01'
def read(p):return json.loads(p.read_text())
def shape(op):
    match=re.fullmatch(r'Switch \{ value: (\d+), cases: (\[.*\]), otherwise: (\d+) \}',op)
    assert match,op
    cases=ast.literal_eval(match[2]);assert isinstance(cases,list) and len(cases)<=16
    assert all(type(v) is int and 0<=v<2**128 and type(t) is int and t>=0 for v,t in cases)
    if len(cases)==1 and cases[0][0]==0:return 'single_zero'
    if cases and all(v<=4095 for v,t in cases):return 'other_small_cases'
    return 'general_or_empty'

with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,12)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    folder=ROOT/'results/composed-fre-runtime-sampling-01';closed=read(folder/'closure.json')
    assert closed['status']=='closed' and closed['all_hashes_verified']
    assert sha(folder/'summary.json')==closed['summary_sha256']
    assert sha(ROOT/closed['evidence'])==closed['evidence_sha256']
    evidence=read(ROOT/closed['evidence'])
    assert all(sha(ROOT/p)==h for p,h in evidence.items())
    original=read(ROOT/'.work/composed-fre-runtime-sampling-01/plan.json')
    raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);output=[]
    for case in original['cases']:
        source=ROOT/'.work'/case['run_id']/'0'
        m=read(source/'jit-code/operations.json');n=read(source/'jit-code/map.json')
        p=read(ROOT/case['profile']);assert sha(ROOT/case['profile'])==case['profile_sha256']
        index=validate(m,n,(source/'jit-code/code.bin').read_bytes(),p,m['pid'])
        coarse=read(ROOT/'results'/case['run_id']/'operation-attribution.json')
        counts=Counter();words=Counter();sampled=Counter();sites=Counter();static=[]
        for row in index['rows']:
            if row['label']!='operation:Switch':continue
            op=p['functions'][row['function']]['operations'][row['pc']];kind=shape(op)
            counts[kind]+=1;words[kind]+=(row['end']-row['offset'])//4
            static.append(dict(function=row['function'],pc=row['pc'],shape=kind,words=(row['end']-row['offset'])//4))
        generated=0
        for root in parse_tree((source/'sample.txt').read_text()):
            for count,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-m['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                rows=[locate(index,o) for o in offsets]
                assert len({(r['function'],r['region_pc'],r['pc'],r['label']) for r in rows})==1
                generated+=count;row=rows[0]
                if row['label']!='operation:Switch':continue
                op=p['functions'][row['function']]['operations'][row['pc']];kind=shape(op)
                sampled[kind]+=count;sites[row['function'],row['pc'],kind,op]+=count
        assert generated==coarse['attributed_generated_samples'] and coarse['unassigned_generated_samples']==0
        assert sum(sampled.values())==coarse['by_label']['operation:Switch']
        output.append(dict(case=case['label'],generated_samples=generated,switch_samples=sum(sampled.values()),
            samples_by_shape=dict(sampled),native_spans_by_shape=dict(counts),native_words_by_shape=dict(words),
            sites=[dict(function=fid,name=p['functions'][fid]['name'],pc=pc,shape=kind,operation=op,samples=count)
                for (fid,pc,kind,op),count in sites.most_common()],static_sites=static))
    for path in [folder/'closure.json',folder/'summary.json',ROOT/closed['evidence'],*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]:
        evidence[str(path.relative_to(ROOT))]=sha(path)
    write(raw/'evidence.json',evidence)
    out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
    write(out/'summary.json',dict(status='passed',source_revision=revision,cases=output,
        evidence=str((raw/'evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'evidence.json'),
        guest_commands=0,performance_measurement=False,profile_used_for_static_identity_only=True))
    print(json.dumps([{k:c[k] for k in ['case','switch_samples','samples_by_shape','native_spans_by_shape']} for c in output]))

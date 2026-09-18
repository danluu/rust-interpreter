"""Join available guarded external reads to exact closed native samples."""
from bisect import bisect_right
from collections import Counter
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from summarize_owned_sample import parse_tree,self_samples
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
def locate(rows,starts,offset):
    i=bisect_right(starts,offset)-1
    assert i>=0 and rows[i]['offset']<=offset<rows[i]['end'] and offset%4==0
    return rows[i]
def selection(rows,starts,offsets,hits):
    assert offsets
    owners=[locate(rows,starts,o) for o in offsets]
    keys={(o['function'],o['region_pc'],o['pc'],o['kind']) for o in owners};assert len(keys)==1
    o=owners[0]
    return hits.get((o['function'],o['pc'])) if o['kind']=='operation' else None
def main(run):
    assert re.fullmatch(r'guarded-value-census-\d{2}',run)
    evidence={};cases=[]
    def bind(p,h=None):
        digest=sha(p)
        if h is not None:assert digest==h,p
        evidence[str(p.relative_to(ROOT))]=digest
    for label in ['block','exhaustive','parser']:
        sample='parser-runtime-sample-01' if label=='parser' else 'scratch-scalar-runtime-sample-'+label+'-01'
        folder=ROOT/'.work'/sample/'0';report_path=ROOT/'.work'/run/(label+'.json');report=read(report_path)
        assert report['status']=='passed' and report['full_code_and_entries_reconstructed'] and report['observation_changes_code'] is False
        mapping_path=folder/'jit-code/operations.json';mapping=read(mapping_path)
        assert mapping['profiled'] is False and mapping['complete'] and mapping['reconstructed_bytes_match']
        assert report['code_sha256']==mapping['code_sha256']==sha(folder/'jit-code/code.bin')
        old_path=ROOT/'results'/sample/'operation-attribution.json';old=read(old_path)
        assert old['status']=='passed' and old['unassigned_generated_samples']==0
        for p,h in old['evidence'].items():bind(ROOT/p,h)
        rows=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        starts=[s['offset'] for s in rows];assert starts==sorted(set(starts))
        hits={}
        for f in report['functions']:
            for h in f['reads']:
                key=(f['id'],h['pc']);assert key not in hits and h['operation'] in ['Load','Copy'] and 0<h['size']<=16 and h['offset']>=0
                hits[key]=dict(h,function=f['id'],name=f['name'])
        words=sum((r['end']-r['offset'])//4 for r in rows if r['kind']=='operation' and (r['function'],r['pc']) in hits)
        sampled=Counter();sites=Counter();generated=0
        for root in parse_tree((folder/'sample.txt').read_text()):
            for count,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                hit=selection(rows,starts,offsets,hits);generated+=count
                if hit is not None:sampled[hit['operation']]+=count;sites[hit['function'],hit['pc']]+=count
        assert generated==old['attributed_generated_samples']
        cases.append(dict(case=label,available_read_sites=len(hits),available_read_functions=len({f for f,pc in hits}),available_read_native_words=words,
            generated_samples=generated,selected_samples=sum(sampled.values()),samples_by_operation=dict(sampled),
            sampled_sites=[dict(function=f,pc=pc,name=hits[f,pc]['name'],operation=hits[f,pc]['operation'],size=hits[f,pc]['size'],samples=count) for (f,pc),count in sites.most_common()]))
        for p in [report_path,mapping_path,folder/'jit-code/code.bin',folder/'sample.txt',old_path]:bind(p)
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(out/'attribution.json',dict(status='passed',cases=cases,evidence=evidence,guest_commands=0,performance_measurement=False,
        scope='Exact original operation ownership. Partial perturbed normal-entropy self-PC samples; no speedup inference or dynamic instruction estimate.'))
    print(json.dumps(cases),flush=True)
if __name__=='__main__':main(sys.argv[1])

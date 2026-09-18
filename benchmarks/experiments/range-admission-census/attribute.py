"""Join additional range-group operations to exact closed native samples."""
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
    assert re.fullmatch(r'range-admission-census-\d{2}',run)
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
        operations={(r['function'],r['pc']):r for r in rows if r['kind']=='operation'}
        hits={};groups={};histogram=Counter();accesses=0;retained=0
        for f in report['functions']:
            retained+=f['retained_groups']
            for g in f['groups']:
                group=(f['id'],g['start']);assert group not in groups
                assert 4<=len(g['sites'])<8 and g['start']<g['end'] and 0<g['high']-g['low']<=4096
                groups[group]=dict(g,function=f['id'],name=f['name'])
                histogram[len(g['sites'])]+=1;accesses+=len(g['sites'])
                for h in g['sites']:
                    assert g['start']<=h['pc']<g['end'] and h['size']>0
                    key=(f['id'],h['pc'])
                    owner=operations.get(key)
                    # Zero-word operations exist in the complete map but have no
                    # sampled PC and were excluded from the nonempty interval index.
                    if owner:assert owner['region_pc']==g['start']
                    if key in hits:assert hits[key]['group']==group
                    else:hits[key]=dict(group=group,operation='memory',function=f['id'],name=f['name'])
        words=sum((r['end']-r['offset'])//4 for r in rows if r['kind']=='operation' and (r['function'],r['pc']) in hits)
        sampled=Counter();group_samples=Counter();generated=0
        for root in parse_tree((folder/'sample.txt').read_text()):
            for count,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                hit=selection(rows,starts,offsets,hits);generated+=count
                if hit is not None:
                    sampled[hit['operation']]+=count;group_samples[hit['group']]+=count
        assert generated==old['attributed_generated_samples']
        cases.append(dict(case=label,additional_groups=len(groups),additional_accesses=accesses,
            additional_operation_sites=len(hits),additional_functions=len({f for f,pc in groups}),
            original_operation_words=words,retained_groups=retained,group_histogram=dict(histogram),
            generated_samples=generated,selected_samples=sum(sampled.values()),samples_by_operation=dict(sampled),
            sampled_groups=[dict(function=f,start=start,name=groups[f,start]['name'],
                accesses=len(groups[f,start]['sites']),frame_disjoint=groups[f,start]['frame_disjoint'],samples=count)
                for (f,start),count in group_samples.most_common()]))
        for p in [report_path,mapping_path,folder/'jit-code/code.bin',folder/'sample.txt',old_path]:bind(p)
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(out/'attribution.json',dict(status='passed',cases=cases,evidence=evidence,guest_commands=0,performance_measurement=False,
        scope='Exact original operation ownership for additional 4–7-access groups. Selected operations also contain work a guard would not remove; no guard success rate, net instruction saving or speedup inference. Partial perturbed normal-entropy self-PC samples.'))
    print(json.dumps(cases),flush=True)
if __name__=='__main__':main(sys.argv[1])

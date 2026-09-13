"""Attribute saved native self-PCs to exact small-memory instruction parts."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from profile_vm_transitions import counts
from summarize_owned_sample import parse_tree,self_samples
from workflow_io import write_json as write


def locate(rows,starts,offset):
    i=bisect_right(starts,offset)-1
    assert i>=0 and rows[i]['offset']<=offset<rows[i]['end'] and offset%4==0
    return rows[i]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'memory-operation-parts-census-\d{2}',args.run_id)
    proof_path=ROOT/'results/guarded-local-facts-profile-01/summary.json'
    proof=json.loads(proof_path.read_text())
    assert proof['status']=='passed' and proof['exact_per_pc_counts'] and proof['exact_operation_map_reconstruction']
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [proof_path,Path(__file__),
        ROOT/'scripts/profile_vm_transitions.py',ROOT/'scripts/summarize_owned_sample.py']}
    output=[]
    for index,label in enumerate(['block','exhaustive']):
        folder=ROOT/'.work'/('adopted-runtime-sample-'+label+'-01')/'0'
        report_path=ROOT/'.work'/args.run_id/(label+'.json');report=json.loads(report_path.read_text())
        assert report['status']=='passed' and report['complete_small_memory_partition']
        assert report['exact_full_function_reconstruction'] and report['observer_words_unchanged']
        assert report['guest_commands']==report['executable_code_publications']==0
        map_path=folder/'jit-code/operations.json';mapping=json.loads(map_path.read_text())
        assert report['code_sha256']==mapping['code_sha256']==sha(folder/'jit-code/code.bin')
        old_path=ROOT/'results'/('adopted-runtime-sample-'+label+'-01')/'operation-attribution.json'
        old=json.loads(old_path.read_text());assert old['status']=='passed' and old['unassigned_generated_samples']==0
        assert all(sha(ROOT/p)==h for p,h in old['evidence'].items())
        profile_path=ROOT/proof['raw']/(str(index)+'-profile.json');comparison=proof['comparisons'][index]
        assert sha(profile_path)==comparison['profile_sha256']
        profile=json.loads(profile_path.read_text());accounting=counts(profile,comparison['statistics'])
        rows=[dict(s,function=f['function']) for f in report['functions'] for s in f['memory_spans']]
        starts=[s['offset'] for s in rows];assert starts==sorted(set(starts))
        coarse=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        coarse_starts=[s['offset'] for s in coarse];assert coarse_starts==sorted(set(coarse_starts))
        selected={(f['function'],s['pc']):(s['operation'],s['size']) for f in report['functions'] for s in f['selected']}
        static,weighted,sampled,details,sites=Counter(),Counter(),Counter(),Counter(),Counter()
        represented=set()
        for f in report['functions']:
            fid=f['function'];assert fid not in represented;represented.add(fid)
            assert profile['functions'][fid]['name']==f['name']
            for s in f['memory_spans']:
                assert s['part']!='unclassified' and (s['operation'],s['size'])==selected[fid,s['pc']]
                pf=profile['functions'][fid];assert pf['jit_block_ends'][s['region_start']]==s['region_end']
                hits=pf['jit_blocks'][s['region_start']];words=(s['end']-s['offset'])//4
                static[s['part']]+=words;weighted[s['part']]+=words*hits
        generated=selected_samples=0;ambiguous=[]
        for root in parse_tree((folder/'sample.txt').read_text()):
            for n,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                coarse_rows=[locate(coarse,coarse_starts,o) for o in offsets]
                assert len({(s['function'],s['region_pc'],s['pc'],s['kind']) for s in coarse_rows})==1
                generated+=n;c=coarse_rows[0];identity=(c['function'],c['pc'])
                if c['kind']!='operation' or identity not in selected:continue
                fine=[locate(rows,starts,o) for o in offsets]
                assert all((s['function'],s['pc'])==identity for s in fine)
                groups={(s['part'],s['access']) for s in fine};selected_samples+=n
                if len(groups)!=1:
                    sampled['ambiguous']+=n
                    ambiguous.append(dict(function=c['function'],pc=c['pc'],samples=n,groups=sorted(groups),offsets=offsets))
                    continue
                part,access=next(iter(groups));sampled[part]+=n
                operation,size=selected[identity];details[f'{operation}/{size}:{access}:{part}']+=n
                sites[(c['function'],c['pc'],part,access)]+=n
        assert generated==old['attributed_generated_samples']
        expected=old['by_label'].get('operation:Load',0)+old['by_label'].get('operation:Store',0)
        expected+=sum(n for detail,n in old['by_detail'].items() if detail.startswith('operation:Copy/') and int(detail.split('/')[1])<=16)
        assert selected_samples==expected==sum(sampled.values())
        omitted=[]
        for fid,f in enumerate(profile['functions']):
            if fid in represented:continue
            native=sum(n*(f['jit_block_ends'][pc]-pc) for pc,n in enumerate(f['jit_blocks']) if n)
            if native:omitted.append(dict(function=fid,name=f['name'],native_instructions=native))
        output.append(dict(case=label,functions=len(represented),memory_part_spans=len(rows),
            static_words_by_part=dict(static),weighted_words_by_part=dict(weighted),
            samples_by_part=dict(sampled),samples_by_detail=dict(details),generated_samples=generated,
            selected_samples=selected_samples,ambiguous=ambiguous,omitted_executed_functions=omitted,
            native_instructions=accounting['native_instructions'],
            top_sampled_sites=[dict(function=fid,name=profile['functions'][fid]['name'],pc=pc,part=part,access=access,samples=n)
                for (fid,pc,part,access),n in sites.most_common(30)]))
        for p in [report_path,map_path,old_path,profile_path,folder/'sample.txt',folder/'jit-code/code.bin']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
    result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=True)
    write(result/'attribution.json',dict(status='passed',cases=output,evidence=evidence,guest_commands=0,
        performance_measurement=False,limitation='Exact emitted parts of Load/Store and Copy up to sixteen bytes only. Weighted emitted words are not retired instructions. Saved samples are two short perturbed windows under ordinary entropy; these are not timing results.'))
    for c in output:
        print(json.dumps({k:c[k] for k in ['case','functions','memory_part_spans','samples_by_part','generated_samples','selected_samples']}))


if __name__=='__main__':main()

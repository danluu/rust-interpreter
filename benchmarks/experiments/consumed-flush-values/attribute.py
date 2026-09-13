"""Classify exact saved flush spans using existing logical profiles and self-PCs."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from profile_vm_transitions import counts
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import write_json as write


def reason(row):
    if not row['analysis_available']: return 'liveness_unavailable'
    if row['live_after']: return 'live_in_successor'
    assert row['live_before']
    if not row['tail_consumed']: return 'unexecuted_branch_tail'
    assert row['eligible']
    return 'consumed_last_use'


def locate(rows, starts, offset):
    i = bisect_right(starts, offset)-1
    assert i >= 0 and rows[i]['offset'] <= offset < rows[i]['end'] and offset%4 == 0
    return rows[i]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args(); assert re.fullmatch(r'consumed-flush-values-census-\d{2}', args.run_id)
    proof_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
    proof = json.loads(proof_path.read_text())
    assert proof['status']=='passed' and proof['exact_per_pc_counts'] and proof['exact_operation_map_reconstruction']
    evidence = {str(p.relative_to(ROOT)):sha(p) for p in [proof_path,Path(__file__),
        ROOT/'scripts/profile_vm_transitions.py',ROOT/'scripts/summarize_owned_sample.py']}
    output = []
    for index, label in enumerate(['block','exhaustive']):
        folder = ROOT / '.work' / ('adopted-runtime-sample-'+label+'-01') / '0'
        report_path = ROOT / '.work' / args.run_id / (label+'.json'); report=json.loads(report_path.read_text())
        assert report['status']=='passed' and report['complete_flush_partition']
        assert report['exact_full_function_reconstruction'] and report['observer_words_unchanged']
        assert report['guest_commands']==report['executable_code_publications']==0
        map_path=folder/'jit-code/operations.json'; mapping=json.loads(map_path.read_text())
        assert report['code_sha256']==mapping['code_sha256']==sha(folder/'jit-code/code.bin')
        old_path=ROOT/'results'/('adopted-runtime-sample-'+label+'-01')/'operation-attribution.json'
        old=json.loads(old_path.read_text());assert old['status']=='passed' and old['unassigned_generated_samples']==0
        assert all(sha(ROOT/p)==h for p,h in old['evidence'].items())
        profile_path=ROOT/proof['raw']/(str(index)+'-profile.json')
        comparison=proof['comparisons'][index];assert sha(profile_path)==comparison['profile_sha256']
        profile=json.loads(profile_path.read_text()); accounting=counts(profile,comparison['statistics'])
        rows=[dict(s,function=f['function']) for f in report['functions'] for s in f['flush_spans']]
        starts=[s['offset'] for s in rows];assert starts==sorted(set(starts))
        coarse=[dict(s,function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        coarse_starts=[s['offset'] for s in coarse];assert coarse_starts==sorted(set(coarse_starts))
        static,weighted,sampled,sites=Counter(),Counter(),Counter(),Counter()
        functions=Counter();represented=set()
        for f in report['functions']:
            fid=f['function'];assert fid not in represented;represented.add(fid)
            assert profile['functions'][fid]['name']==f['name']
            for row in f['flush_spans']:
                group=reason(row); assert row['eligible']==(group=='consumed_last_use')
                pf=profile['functions'][fid];assert pf['jit_block_ends'][row['region_start']]==row['region_end']
                hits=pf['jit_blocks'][row['region_start']]; words=(row['end']-row['offset'])//4
                static[group]+=words;weighted[group]+=words*hits
                if row['eligible']:functions[fid]+=words*hits
        generated=flush_samples=0
        for root in parse_tree((folder/'sample.txt').read_text()):
            for n,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                coarse_rows=[locate(coarse,coarse_starts,o) for o in offsets]
                assert len({(s['function'],s['region_pc'],s['pc'],s['kind']) for s in coarse_rows})==1
                generated+=n
                if coarse_rows[0]['kind']!='flush':continue
                fine=[locate(rows,starts,o) for o in offsets]; groups={reason(s) for s in fine}
                assert len(groups)==1, 'ambiguous liveness label in saved sample'
                group=next(iter(groups));sampled[group]+=n;flush_samples+=n
                identities={(s['function'],s['region_start'],s['register']) for s in fine}
                if len(identities)==1:
                    fid,region,register=next(iter(identities));sites[(fid,region,register,group)]+=n
        assert generated==old['attributed_generated_samples']
        assert flush_samples==old['by_label']['flush']
        omitted=[]
        for fid,f in enumerate(profile['functions']):
            if fid in represented:continue
            native=sum(n*(f['jit_block_ends'][pc]-pc) for pc,n in enumerate(f['jit_blocks']) if n)
            if native:omitted.append(dict(function=fid,name=f['name'],native_instructions=native))
        output.append(dict(case=label,functions=len(represented),flush_value_spans=len(rows),
            static_words_by_reason=dict(static),weighted_words_by_reason=dict(weighted),
            samples_by_reason=dict(sampled),generated_samples=generated,flush_samples=flush_samples,
            omitted_executed_functions=omitted,native_instructions=accounting['native_instructions'],
            top_eligible_functions=[dict(function=fid,name=profile['functions'][fid]['name'],weighted_words=n)
                for fid,n in functions.most_common(20)],
            top_sampled_sites=[dict(function=fid,region=region,register=reg,reason=group,samples=n)
                for (fid,region,reg,group),n in sites.most_common(30)]))
        for p in [report_path,map_path,old_path,profile_path,folder/'sample.txt',folder/'jit-code/code.bin']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
    result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=True)
    write(result/'attribution.json',dict(status='passed',cases=output,evidence=evidence,guest_commands=0,
        performance_measurement=False,limitation='Existing whole-CFG liveness and exact actual-emitter spans only; no stores are removed. Weighted emitted words are not retired instruction measurements. Samples are two retained short perturbed windows, not timing evidence.'))
    for c in output:print(json.dumps({k:v for k,v in c.items() if k not in ['top_eligible_functions','top_sampled_sites','omitted_executed_functions']}))


if __name__=='__main__':main()

"""Count actual continuation eligibility and exact counter-update PCs in saved evidence."""
from collections import Counter
from pathlib import Path
import argparse
import json
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from profile_vm_transitions import counts
from summarize_owned_sample import parse_tree,self_samples
from workflow_io import write_json as write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'native-continuation-census-\d{2}',args.run_id)
    work=ROOT/'.work'/args.run_id;plan=json.loads((work/'plan.json').read_text())
    frozen=plan['frozen'];assert all(sha(ROOT/p)==h for p,h in frozen.items())
    proof_path=ROOT/'results/guarded-local-facts-profile-01/summary.json';proof=json.loads(proof_path.read_text())
    assert proof['status']=='passed' and proof['exact_per_pc_counts'] and proof['exact_operation_map_reconstruction']
    protocol_path=ROOT/'results/native-protocol-census-01/attribution.json';protocol=json.loads(protocol_path.read_text())
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [proof_path,protocol_path,Path(__file__)]};output=[]
    for index,label in enumerate(['block','exhaustive']):
        report_path=work/(label+'.json');report=json.loads(report_path.read_text())
        assert report['status']=='passed' and report['exact_baseline_reconstruction']
        assert report['guest_commands']==report['executable_code_publications']==0
        folder=ROOT/'.work'/('adopted-runtime-sample-'+label+'-01')/'0'
        map_path=folder/'jit-code/operations.json';mapping=json.loads(map_path.read_text())
        code_path=folder/'jit-code/code.bin';code=code_path.read_bytes()
        assert sha(code_path)==mapping['code_sha256']==report['code_sha256']
        profile_path=ROOT/proof['raw']/(str(index)+'-profile.json');comparison=proof['comparisons'][index]
        assert sha(profile_path)==comparison['profile_sha256'];profile=json.loads(profile_path.read_text())
        accounting=counts(profile,comparison['statistics'])
        fine_path=ROOT/'.work/native-protocol-census-01'/(label+'.json');fine=json.loads(fine_path.read_text())
        assert fine['code_sha256']==report['code_sha256'] and fine['complete_partition']
        static=Counter();weighted=Counter();represented=set();sites=[]
        for f in report['functions']:
            fid=f['function'];assert fid not in represented;represented.add(fid)
            pf=profile['functions'][fid];assert pf['name']==f['name']
            for c in f['calls']:
                pc=c['pc'];hits=pf['jit_blocks'][pc];assert pf['jit_block_ends'][pc]==pc+1
                eligible=c['native_return_offset'] is not None
                kind='eligible' if eligible else ('one_past' if c['one_past_code'] else 'unsupported')
                static[kind]+=1;weighted[kind]+=hits
                if eligible:
                    assert 0<c['native_return_offset']<len(code) and c['native_return_offset']%4==0
                    assert c['immediate_store_words'] in [2,3]
                    weighted['prospective_immediate_store_words']+=hits*c['immediate_store_words']
                sites.append(dict(function=fid,name=f['name'],count=hits,**c))
        omitted=[]
        for fid,pf in enumerate(profile['functions']):
            if fid not in represented and any(pf['jit_blocks']):omitted.append(fid)
        assert not omitted,omitted
        native_calls=sum(weighted[k] for k in ['eligible','one_past','unsupported'])
        assert native_calls==comparison['statistics']['jit_resumable_calls']
        counters={};counter_static=Counter();counter_weighted=Counter();dispatch={}
        for span in fine['spans']:
            op=span['operation'];pc=span['pc'];pf=profile['functions'][span['function']]
            hits=pf['jit_blocks'][pc];assert pf['jit_block_ends'][pc]==pc+1
            if span['kind']=='return_dispatch':
                for offset in range(span['offset'],span['end'],4):dispatch[offset]=True
            if (op,span['kind']) not in [('Call','call_publish_frame'),('Return','return_restore_frame')]:continue
            field=report['counter_offsets'][op];assert field%8==0 and field//8<4096
            pattern=(0xf9400000|((field//8)<<10)|(19<<5)|9,0x91000529,
                     0xf9000000|((field//8)<<10)|(19<<5)|9)
            found=[offset for offset in range(span['offset'],span['end']-11,4)
                if struct.unpack_from('<III',code,offset)==pattern]
            assert len(found)==1,(label,span,found)
            counter_static[op]+=1;counter_weighted[op]+=hits
            for offset in range(found[0],found[0]+12,4):assert offset not in counters;counters[offset]=op
        assert counter_weighted['Call']==native_calls
        assert counter_weighted['Return']==comparison['statistics']['jit_resumable_returns']
        samples=Counter();ambiguous=[]
        for root in parse_tree((folder/'sample.txt').read_text()):
            for n,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                kinds={('counter_'+counters[o]) if o in counters else ('return_dispatch' if o in dispatch else 'other') for o in offsets}
                if len(kinds)!=1:ambiguous.append(dict(samples=n,offsets=offsets,kinds=sorted(kinds)));samples['ambiguous']+=n
                else:samples[next(iter(kinds))]+=n
        assert not ambiguous,ambiguous
        previous=protocol['cases'][index];assert previous['case']==label
        assert sum(samples.values())==previous['generated_samples']
        assert samples['return_dispatch']==previous['fine_samples']['Return/return_dispatch']
        output.append(dict(case=label,functions=len(represented),static_continuations=dict(static),
            weighted_continuations=dict(weighted),native_calls=native_calls,
            native_returns=comparison['statistics']['jit_resumable_returns'],counter_sites=dict(counter_static),
            counter_updates=dict(counter_weighted),counter_weighted_emitted_words=3*sum(counter_weighted.values()),
            samples=dict(samples),generated_samples=sum(samples.values()),ambiguous_samples=ambiguous,
            omitted_executed_functions=omitted,logical_accounting=accounting,
            top_calls=sorted(sites,key=lambda c:-c['count'])[:20]))
        for p in [report_path,map_path,code_path,profile_path,fine_path,folder/'sample.txt']:evidence[str(p.relative_to(ROOT))]=sha(p)
        print(label,'calls',native_calls,'eligible',weighted['eligible'],'samples',dict(samples),flush=True)
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    write(ROOT/'results'/args.run_id/'attribution.json',dict(status='passed',cases=output,evidence=evidence,
        guest_commands=0,performance_measurement=False,
        limitation='Typed continuation coverage is weighted by bound-entropy native Call hits, not individual observed Returns. Other frames still need original lookup. Counter words are actual code patterns; weighted emitted words and sampled PCs are not retired instructions or an end-to-end gain.'))


if __name__=='__main__':main()

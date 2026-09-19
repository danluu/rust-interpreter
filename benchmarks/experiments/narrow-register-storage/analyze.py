"""Join logical narrow widths to native traffic and interpreter repair bounds."""
from bisect import bisect_right
from collections import Counter
import hashlib,json,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/ordinary-memory-traffic'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/ordinary-register-census'))
from compare_saved_runtime import sha
from workflow_io import write_json as write
from summarize_owned_sample import parse_tree,self_samples
from traffic import analyze
from linear import direct_target
from regions import groups
RUN='narrow-register-storage-census-01'
def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())
def main():
    raw=ROOT/'.work'/RUN;plan=read(raw/'plan.json');typed=read(raw/'typed.json')
    assert typed['status']=='passed' and typed['artifact_sha256']==plan['artifact_sha256']
    proofs=typed['functions'];assert [r['function'] for r in proofs]==list(range(len(proofs)))
    baseline=read(ROOT/'results/runtime-composition-profile-02/summary.json')
    sampled=read(ROOT/'results/adopted-current-runtime-sampling-02/summary.json')
    cases=[];details=[]
    for case in sampled['cases']:
        folder=ROOT/'.work'/case['run_id']/'0';mapping=read(folder/'jit-code/operations.json')
        code=(folder/'jit-code/code.bin').read_bytes()
        assert len(code)<=16*1024**2 and len(code)==mapping['code_bytes'] and sha(folder/'jit-code/code.bin')==mapping['code_sha256']
        assert mapping['schema_version']==2 and mapping['complete'] and mapping['reconstructed_bytes_match']
        assert not mapping['profiled'] and mapping['persistent_registers'] and mapping['resumable_calls']
        words=list(struct.unpack('<'+'I'*(len(code)//4),code))
        targets={t for pc,w in enumerate(words) if (t:=direct_target(w,pc)) is not None}
        spans=[dict(s,function=f['function'],name=f['name']) for f in mapping['functions'] for s in f['spans'] if s['offset']<s['end']]
        starts=[s['offset'] for s in spans]
        assert len(spans)<=2_000_000 and starts==sorted(set(starts)) and starts[0]==0 and spans[-1]['end']==len(code)
        assert all(a['end']==b['offset'] for a,b in zip(spans,spans[1:]))
        def locate(offset):
            pos=bisect_right(starts,offset)-1
            assert pos>=0 and spans[pos]['offset']<=offset<spans[pos]['end'] and offset%4==0
            return spans[pos]
        accesses={};static=Counter();site_rows=[]
        for region in groups(spans):
            fid=region['key'][0];proof=proofs[fid]
            assert proof['name']==region['spans'][0]['name']
            eligible=set(proof['narrow'] or []);assert all(0<=r<proof['registers'] for r in eligible)
            assert not proof['declined'] or not eligible
            first,last=region['offset']//4,region['end']//4
            local,_=analyze(words[first:last],{pc-first for pc in range(first,last) if pc in targets})
            for pc,item in local.items():
                assert item['slot']<proof['registers']
                if item['half']!='high':continue
                offset=4*(first+pc);assert offset not in accesses
                admitted=item['slot'] in eligible;accesses[offset]=(admitted,item['direction'])
                static[('eligible_' if admitted else 'full_or_unknown_')+item['direction']]+=1
                if admitted:
                    span=locate(offset)
                    site_rows.append(dict(offset=offset,function=fid,name=proof['name'],register=item['slot'],direction=item['direction'],
                        pc=span['pc'],region_pc=span['region_pc'],span_kind=span['kind'],word=f'{words[offset//4]:08x}'))
        samples=Counter();by_span=Counter();by_function=Counter();generated=0
        for root in parse_tree((folder/'sample.txt').read_text()):
            for count,frame,_ in self_samples(root):
                if '<unknown binary>' not in frame:continue
                assert '...' not in frame
                offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)];assert offsets
                owners=[locate(o) for o in offsets]
                assert len({(o['function'],o['pc'],o['region_pc'],o['kind']) for o in owners})==1
                labels={(('eligible_high_' if accesses[o][0] else 'other_high_')+accesses[o][1]) if o in accesses else 'other_generated' for o in offsets}
                label=next(iter(labels)) if len(labels)==1 else 'ambiguous'
                samples[label]+=count;generated+=count
                if label.startswith('eligible_high_'):
                    by_span[owners[0]['kind']]+=count;by_function[owners[0]['function']]+=count
                details.append(dict(case=case['case'],samples=count,label=label,function=owners[0]['function'],offsets=offsets))
        assert generated==case['attributed_generated_samples']==sum(samples.values())
        index={'block':0,'exhaustive':1}[case['case']]
        prior,=[r for r in baseline['comparisons'] if r['index']==index and r['mode']=='control']
        cost=typed['profiles'][index]
        assert Path(cost['path'])==ROOT/prior['profile_path'] and cost['sha256']==prior['profile_sha256']==sha(Path(cost['path']))
        assert [r['function'] for r in cost['functions']]==list(range(len(proofs)))
        work={k:sum(r['work'][k] for r in cost['functions']) for k in
            ['interpreted_instructions','interpreted_instructions_with_narrow_reads','narrow_read_operands','unique_narrow_read_operands']}
        assert work['interpreted_instructions']==prior['statistics']['instructions']-prior['statistics']['jit_instructions']
        cases.append(dict(case=case['case'],generated_samples=generated,static_high_accesses=dict(static),
            conservative_interpreter_work=work,native_entries=prior['statistics']['jit_entries'],
            sampled_categories=dict(samples),eligible_samples_by_span=dict(by_span),
            top_eligible_functions=[dict(function=fid,name=proofs[fid]['name'],samples=n) for fid,n in by_function.most_common(15)],
            unassigned_generated_samples=0))
        write(raw/(case['case']+'-sites.json'),site_rows)
        print(json.dumps(cases[-1]),flush=True)
    write(raw/'details.json',details)
    write(raw/'attribution.json',dict(status='passed',cases=cases,typed_functions=len(proofs),
        declined_functions=sum(r['declined'] for r in proofs),
        eligible_registers=sum(len(r['narrow'] or []) for r in proofs),
        guest_commands=0,executable_code_publications=0,performance_measurement=False))
if __name__=='__main__':main()

"""Census exact old immediate sequences in already closed native samples."""
from collections import Counter
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/tree-bridge-native-sampling'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples

MASK=(1<<64)-1

def decode(words,start,end):
    word=words[start]
    if word & 0xffe00000 != 0xd2800000:return None  # 64-bit MOVZ, shift zero
    reg=word&31;value=(word>>5)&0xffff;at=start+1;last=0
    while at<end:
        word=words[at]
        if word&0xff80001f != 0xf2800000|reg:break
        shift=(word>>21)&3;part=(word>>5)&0xffff
        if shift<=last or part==0:break
        value|=part<<(16*shift);last=shift;at+=1
    pieces=[(value>>(16*i))&0xffff for i in range(4)]
    zero_cost=max(1,sum(v!=0 for v in pieces))
    ones_cost=max(1,sum(v!=0xffff for v in pieces))
    return dict(start=start,end=at,reg=reg,value=value,old_words=at-start,
        shifted_zero_words=zero_cost,minimal_wide_words=min(zero_cost,ones_cost),
        removable_zero_seed=at-start>zero_cost)


def scan(words,ranges):
    sequences=[];classes={};end=0
    for row in ranges:
        assert row['offset']==end and row['end']>end and row['end']%4==0 and row['end']<=4*len(words)
        at=end//4
        while at<row['end']//4:
            found=decode(words,at,row['end']//4)
            if found is None:at+=1;continue
            found['kind']=row['kind'];sequences.append(found)
            for pos in range(at,found['end']):
                classes[pos]=(found['removable_zero_seed'] and pos==at,
                    found['old_words']>found['minimal_wide_words'],found['kind'])
            at=found['end']
        end=row['end']
    assert end==4*len(words)
    return sequences,classes


def main():
    name='immediate-materialization-census-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,10)
        controls_path=ROOT/'results/immediate-materialization-controls-01/summary.json'
        controls=json.loads(controls_path.read_text());assert controls['status']=='passed' and controls['tests']==6 and controls['guest_commands']==0
        controls_raw=ROOT/controls['raw']
        assert sha(controls_raw/'plan.json')==controls['plan_sha256'] and sha(controls_raw/'record.json')==controls['record_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads((controls_raw/'plan.json').read_text())['frozen'].items())
        closure_path=ROOT/'results/tree-bridge-native-sampling-01/closure.json'
        closure=json.loads(closure_path.read_text())
        assert closure['status']=='passed' and closure['guest_executions']==2
        paths=[closure_path,controls_path,controls_raw/'plan.json',controls_raw/'record.json',Path(__file__),Path(__file__).with_name('PLAN.md'),Path(__file__).with_name('test_census.py'),
               ROOT/'benchmarks/experiments/tree-bridge-native-sampling/summarize_owned_sample.py',
               ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
        cases=[]
        for label in ['block','exhaustive']:
            run='tree-bridge-native-sample-'+label+'-01';folder=ROOT/'.work'/run/'0'
            inputs=[ROOT/'results'/run/'summary.json',ROOT/'results'/run/'generated-attribution.json',
                    folder/'record.json',folder/'sample.txt',folder/'jit-code/map.json',folder/'jit-code/code.bin']
            for p in inputs:assert sha(p)==closure['evidence'][str(p.relative_to(ROOT))]
            paths+=inputs
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
        work=ROOT/'.work'/name;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            frozen=frozen,guest_commands=0,executable_publications=0,performance_measurement=False))
        for label in ['block','exhaustive']:
            run='tree-bridge-native-sample-'+label+'-01';folder=ROOT/'.work'/run/'0'
            summary=json.loads((ROOT/'results'/run/'summary.json').read_text());sample,=summary['samples']
            record=json.loads((folder/'record.json').read_text());native=json.loads((folder/'jit-code/map.json').read_text())
            attribution=json.loads((ROOT/'results'/run/'generated-attribution.json').read_text())
            code=(folder/'jit-code/code.bin').read_bytes()
            assert record['identity']['status']=='finished' and record['identity']['returncode']==0
            assert sample['pid']==record['identity']['pid']==native['pid']
            assert summary['options']['jit_tree_bridge'] and not native['profiled']
            assert len(code)==native['code_bytes']==record['statistics']['jit_bytes']
            words=[w[0] for w in struct.iter_unpack('<I',code)]
            sequences,classes=scan(words,native['ranges'])
            counts=Counter();base=native['arena_base']
            for root in parse_tree((folder/'sample.txt').read_text()):
                for count,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame:continue
                    addresses=[int(a,16) for a in re.findall(r'0x([0-9a-f]+)',frame)]
                    if not addresses or '...' in frame:counts['unresolved']+=count;continue
                    assert all(0<=a-base<len(code) and (a-base)%4==0 for a in addresses)
                    counts['generated']+=count
                    hits={classes.get((a-base)//4) for a in addresses}
                    if len(hits)!=1:
                        if any(h is not None for h in hits):counts['ambiguous_sequence']+=count
                        continue
                    hit=hits.pop()
                    if hit is None:continue
                    counts['any_immediate_sequence']+=count
                    if hit[0]:counts['removable_zero_seed']+=count
                    if hit[1]:counts['shortenable_whole_sequence']+=count
            assert counts['generated']==attribution['attributed_generated_samples']
            values=Counter(s['value'] for s in sequences if s['removable_zero_seed'])
            result=dict(case=label,code_bytes=len(code),sequences=len(sequences),
                old_sequence_words=sum(s['old_words'] for s in sequences),
                shifted_zero_words=sum(s['shifted_zero_words'] for s in sequences),
                minimal_wide_words=sum(s['minimal_wide_words'] for s in sequences),
                self_pc_counts=dict(counts),top_shifted_zero_values=[dict(value=hex(v),sequences=n) for v,n in values.most_common(12)])
            cases.append(result);print(json.dumps(result),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/name;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',cases=cases,guest_commands=0,executable_publications=0,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),performance_measurement=False,
            limitation='Partial perturbed samples from parked shared-cursor bridge; whole-sequence samples are not removable cost; no latency prediction or adoption claim.'))

if __name__=='__main__':main()

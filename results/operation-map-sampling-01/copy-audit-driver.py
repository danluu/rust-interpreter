from pathlib import Path
import json,struct,sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/operation-map'))
from compare_saved_runtime import sha,acquire_lock
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
from maps import validate
from attribute import assign
with (ROOT/'.work/benchmark.lock').open('a') as lock:
 acquire_lock(lock,45);require_space(ROOT,8)
 outputs=[];evidence={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
 proof_path=ROOT/'results/memory-operands-profile-01/summary.json';proof=json.loads(proof_path.read_text());evidence[str(proof_path.relative_to(ROOT))]=sha(proof_path)
 for index,label in enumerate(['block','exhaustive']):
  folder=ROOT/'.work'/('operation-map-sample-'+label+'-01')/'0'
  report_path=ROOT/'results'/('operation-map-sample-'+label+'-01')/'operation-attribution.json'
  report=json.loads(report_path.read_text());assert report['status']=='passed'
  for p,h in report['evidence'].items():assert sha(ROOT/p)==h
  profile_path=ROOT/proof['raw']/f'{index}-profile.json';assert sha(profile_path)==proof['comparisons'][index]['profile_sha256']
  profile=json.loads(profile_path.read_text())
  code=(folder/'jit-code/code.bin').read_bytes()
  maps=[json.loads((folder/'jit-code'/p).read_text()) for p in ['operations.json','map.json']]
  checked=validate(maps[0],maps[1],code,profile,maps[0]['pid'])
  frames=[x for root in parse_tree((folder/'sample.txt').read_text()) for x in self_samples(root)]
  _,sites,unresolved=assign(checked,maps[0]['arena_base'],frames);assert not unresolved
  static=Counter();samples=Counter();words=Counter();examples={}
  for row in checked['rows']:
   if row['label']!='operation:Copy':continue
   op=profile['functions'][row['function']]['operations'][row['pc']]
   if not op.endswith('size: 8 }'):continue
   emitted=[x[0] for x in struct.iter_unpack('<I',code[row['offset']:row['end']])]
   def local(rd):
    final=0x8b000000|(rd<<16)|(2<<5)|rd
    for a,b in zip(emitted,emitted[1:]):
     if b==final and (a&0xffc003ff==0x91000000|(1<<5)|rd or a==0x8b000000|(rd<<16)|(1<<5)|rd):return True
    return False
   forwarded=0xf9400169 not in emitted
   category=('forwarded' if forwarded else 'local_source' if local(11) else 'checked_source')+' / '+('local_destination' if local(12) else 'checked_destination')
   key=(row['function'],row['region_pc'],row['pc'],row['kind'],row['label'])
   n=sites[key]
   static[category]+=1;words[category]+=len(emitted);samples[category]+=n
   if category not in examples or n>examples[category]['samples']:
    examples[category]=dict(function=row['function'],name=profile['functions'][row['function']]['name'],pc=row['pc'],operation=op,samples=n,words=[f'{w:08x}' for w in emitted])
  assert sum(samples.values())==report['by_detail']['operation:Copy/8']
  outputs.append(dict(case=label,copy8_samples=sum(samples.values()),sample_categories=dict(samples),static_operations=dict(static),static_words=dict(words),examples=examples))
  for p in [report_path,profile_path,folder/'record.json',folder/'jit-code/operations.json',folder/'jit-code/map.json',folder/'jit-code/code.bin',folder/'sample.txt']:
   evidence[str(p.relative_to(ROOT))]=sha(p)
 destination=ROOT/'results/operation-map-copy-audit-01';destination.mkdir(exist_ok=False)
 write(destination/'summary.json',dict(status='passed',guest_executions=0,performance_measurement=False,cases=outputs,evidence=evidence,limitation='Exact existing-emitter local-address/load patterns inside validated eight-byte Copy spans. This classifies saved code and samples; it is not a compiler safety fact or predicted latency saving.'))
 print(json.dumps([{k:v for k,v in row.items() if k!='examples'} for row in outputs]))

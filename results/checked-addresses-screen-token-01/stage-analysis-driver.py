from pathlib import Path
import json,statistics,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
with (ROOT/'.work/benchmark.lock').open('a') as lock:
 acquire_lock(lock,45)
 result_path=ROOT/'results/checked-addresses-screen-token-01/summary.json'
 result=json.loads(result_path.read_text());assert result['commands']==40 and result['gate_passed'] is False
 raw=ROOT/result['raw'];path=raw/'records.json';assert sha(path)==result['records_sha256']
 rows=json.loads(path.read_text());assert len(rows)==40
 pairs=[]
 for state in range(1,6):
  modes={r['mode']:r for r in rows if r['cycle']==0 and r['state']==state}
  assert set(modes)=={'baseline','duplicate','candidate','anchor','native'}
  assert len({r['source_sha256'] for r in modes.values()})==1
  pair=dict(state=state)
  for name,key in [('cargo','cargo_seconds'),('execution','execution_seconds'),('ready','build_to_ready_seconds')]:
   values={mode:modes[mode]['launch'][key] for mode in ['baseline','duplicate','candidate']}
   assert all(v>0 for v in values.values())
   pair[name]=dict(candidate_baseline=values['candidate']/values['baseline'],duplicate_baseline=values['duplicate']/values['baseline'])
  pairs.append(pair)
 metrics={name:dict(paired_candidate_baseline=statistics.median(p[name]['candidate_baseline'] for p in pairs),maximum_duplicate_deviation=max(abs(p[name]['duplicate_baseline']-1) for p in pairs)) for name in ['cargo','execution','ready']}
 output=dict(status='passed',new_commands=0,whole_command_gate_changed=False,stages_are_explanatory_only=True,pairs=pairs,metrics=metrics,input_records_sha256=sha(path),input_summary_sha256=sha(result_path),driver_sha256=sha(Path(__file__)))
 write(result_path.with_name('stage-analysis.json'),output)
 print(json.dumps(metrics),flush=True)

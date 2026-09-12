from pathlib import Path
import hashlib,json,statistics
root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
controller=json.loads((work/'local-analysis-screen-controller.json').read_text())
continuation=json.loads((work/'local-analysis-continuation-controller.json').read_text())
assert len(controller['calls'])==10 and all(c['returncode']==0 for c in controller['calls'])
assert continuation['original_controller_sha256']==hashlib.sha256((work/'local-analysis-screen-controller.json').read_bytes()).hexdigest()
assert continuation['planned_commands']==controller['planned_commands'][10:]
assert continuation.get('status')=='complete' and len(continuation['calls'])==2 and all(c['returncode']==0 for c in continuation['calls'])

rows=[];aggregate={}
for project in ['token','pgrust']:
 pairs=[]
 for i in range(1,4):
  name=f'local-analysis-{project}-20260912-{i:02}'
  folder=root/'results'/name
  report=json.loads((folder/'summary.json').read_text())
  verify=json.loads((folder/'verification.json').read_text())
  assert verify['paired_bytecode_identical'] and verify['build_to_ready_metrics_verified'] and verify['restored_original_build_and_execution_verified']
  ps=report['comparison']['pairs'];assert len(ps)==5
  pairs.extend(ps)
  row={'run':name,'pairs':len(ps),'summary_sha256':hashlib.sha256((folder/'summary.json').read_bytes()).hexdigest()}
  for suffix,label in [('seconds','wall'),('cpu_seconds','cpu')]:
   ratios=[p['candidate_build_to_ready_'+suffix]/p['baseline_build_to_ready_'+suffix] for p in ps]
   row[label]={'ratios':ratios,'median':statistics.median(ratios),'min':min(ratios),'max':max(ratios)}
  row['regression_guard_pass']=all(row[k]['median']<=1.05 for k in ['wall','cpu'])
  rows.append(row)
 aggregate[project]={'pairs':len(pairs)}
 for suffix,label in [('seconds','wall'),('cpu_seconds','cpu')]:
  ratios=[p['candidate_build_to_ready_'+suffix]/p['baseline_build_to_ready_'+suffix] for p in pairs]
  aggregate[project][label]={'median':statistics.median(ratios),'min':min(ratios),'max':max(ratios)}
pass_screen=(aggregate['token']['wall']['median']<=.95 and aggregate['token']['cpu']['median']<1 and all(aggregate['pgrust'][k]['median']<=1.05 for k in ['wall','cpu']) and all(r['regression_guard_pass'] for r in rows))
result={'decision':'proceed to public confirmations' if pass_screen else 'park; fixed build screen not passed','screen_pass':pass_screen,'aggregate':aggregate,'histories':rows,'all_planned_runs_included':True,'aa_noise_subtracted':False,'unstarted_final_history_continued_after_admission_stop':True,'continuation_sha256':hashlib.sha256((work/'local-analysis-continuation-controller.json').read_bytes()).hexdigest(),'controller_sha256':hashlib.sha256((work/'local-analysis-screen-controller.json').read_bytes()).hexdigest()}
with (work/'local-analysis-screen-assessment.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))

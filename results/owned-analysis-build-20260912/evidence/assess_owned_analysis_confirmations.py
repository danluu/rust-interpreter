from pathlib import Path
import hashlib,json,math,statistics

root=Path(__file__).resolve().parents[2]
work=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
plan=read(work/'owned-analysis-public-confirmation-plan.json')
controller=read(work/'owned-analysis-confirmation-controller.json')
assert controller['status']=='complete' and len(controller['calls'])==4
assert all(c['returncode']==0 and c['status']=='complete' for c in controller['calls'])
assert [{'label':c['label'],'command':c['command']} for c in controller['calls']]==plan['commands']==controller['planned_commands']
for name,digest in controller['proofs'].items():assert sha(root/name)==digest,name
screen=read(work/'owned-analysis-screen-assessment.json');assert screen['screen_pass'] and screen['all_planned_runs_included']
assert {r['run'] for r in screen['histories']}=={f'owned-analysis-{p}-20260912-{i:02}' for p in ['token','pgrust'] for i in range(1,4)}
assert len(controller['admissions'])==2
for admission,case,threshold in zip(controller['admissions'],plan['cases'],[7.34,21.74]):
 assert admission['label']==case['run_id'] and admission['minimum_gib']==threshold
 assert admission['free_bytes']>=threshold*2**30 and admission['lock_wait_started']<=admission['time']<=admission['lock_released_at']
rows=[]
for case in plan['cases']:
 name=case['run_id'];folder=root/'results'/name
 report=read(folder/'summary.json');verify=read(folder/'verification.json')
 for key in ['paired_bytecode_identical','build_to_ready_metrics_verified','restored_original_build_and_execution_verified']:
  assert verify[key],(name,key)
 for key in ['project','revision','cycles','tests','initial_mode_order']:
  assert report[key]==case[key],(name,key)
 assert report['workflow']==case['workflow'],(name,'workflow')
 assert len(report['edits'])==case['edit_count']
 for key,value in {'batch':True,'build_tool_opt_level':0,'instruction_limit':100000000000,'allocation_limit':150000,
                   'inline_leaves':True,'baseline_inline_leaves':True,'trap_unsupported_calls':True,'run_try_callbacks':True,
                   'guest_mir_opt_level':3,'guest_mir_inline_scale':8,'minimum_free_gib':1}.items():
  assert report[key]==value,(name,key)
 for mode in ['baseline','candidate']:
  manifest=plan[mode];tools=report['tool_builds'][mode]
  assert tools['tool_key']==manifest['tool_key'] and tools['engine']=='jit'
  assert tools['vm_sha256']==manifest['binaries']['rust-interp-vm']
  assert tools['exporter_sha256']==manifest['binaries']['rust-interp-mir-export']
  assert tools['jit_resumable_calls'] and tools['jit_persistent_registers']
  assert not tools['jit_native_calls'] and not tools['jit_native_call_stubs']
 raw=root/report['raw'];assert raw==root/'.work/runs'/name
 records=read(raw/'records.json');checks=read(raw/'check-records.json')
 assert len(records)==case['primary_commands'] and sum(len(r['calls']) for r in records)==case['primary_commands']
 assert len(checks)==case['check_commands']
 assert sum(len(r.get('artifacts',[])) for r in records)==case['artifacts']
 edited={}
 for record in records:
  if record['phase']!='edit' or record['mode']=='native':continue
  assert record['tests']==case['tests'] and len(record['calls'])==1
  call=record['calls'][0];assert call['returncode']==0
  messages=[line.removeprefix('rust-interp-launch: ') for line in call['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
  assert len(messages)==1 and json.loads(messages[0])==call['launch']
  launch=call['launch'];mode=record['mode']
  assert launch['tool_key']==plan[mode]['tool_key']
  assert launch['compiler_wrapper']['sha256']==plan[mode]['binaries']['rust-interp-rustc-wrapper']
  values={'seconds':launch['build_to_ready_seconds'],'cpu_seconds':launch['build_to_ready_cpu']['total_seconds']}
  assert all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in values.values())
  key=(record['cycle'],record['state'],mode);assert key not in edited
  edited[key]={'source':record['source_sha256'],**values}
 pairs=report['comparison']['pairs'];assert len(pairs)==case['edited_pairs'] and len(edited)==2*len(pairs)
 result={'run':name,'project':case['project'],'pairs':len(pairs),'summary_sha256':sha(folder/'summary.json'),
         'verification_sha256':sha(folder/'verification.json'),'records_sha256':sha(raw/'records.json')}
 for suffix,label in [('seconds','wall'),('cpu_seconds','cpu')]:
  ratios=[]
  for pair in pairs:
   values={}
   for mode in ['baseline','candidate']:
    record=edited[(pair['cycle'],pair['state'],mode)]
    assert record['source']==pair['source_sha256']
    assert math.isclose(record[suffix],pair[mode+'_build_to_ready_'+suffix],rel_tol=1e-12,abs_tol=1e-12)
    values[mode]=record[suffix]
   ratios.append(values['candidate']/values['baseline'])
  result[label]={'ratios':ratios,'median':statistics.median(ratios),'min':min(ratios),'max':max(ratios)}
 result['pass']=all(result[label]['median']<=1.05 for label in ['wall','cpu']);rows.append(result)
passed=all(row['pass'] for row in rows)
result={'decision':'qualified for production review' if passed else 'park; public confirmation guard failed',
        'confirmations_pass':passed,'complete_screen_pass':True,'cases':rows,'all_planned_runs_included':True,
        'aa_noise_subtracted':False,'controller_sha256':sha(work/'owned-analysis-confirmation-controller.json')}
with (work/'owned-analysis-confirmation-assessment.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))

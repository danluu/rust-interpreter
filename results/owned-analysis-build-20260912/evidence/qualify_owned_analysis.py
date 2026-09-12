from pathlib import Path
import hashlib,json,re,shutil
root=Path(__file__).resolve().parents[2];b=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
q={'tests':{},'source_commit':'04bb082','frozen_baseline_runtime':True,'common_scripts_unchanged':True}
for mode in ['debug','release']:
 assert json.loads((b/f'owned-analysis-{mode}-tests.json').read_text())['returncode']==0
 rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (b/f'owned-analysis-{mode}-tests.log').read_text())
 counts=dict(zip(['passed','failed','ignored'],[sum(int(row[i]) for row in rows) for i in range(3)]))
 assert counts=={'passed':388,'failed':0,'ignored':1},counts
 q['tests'][mode]=counts
for label in ['owned-analysis-tools-build','owned-analysis-tools-install','owned-analysis-fixture-tests']:
 assert json.loads((b/f'{label}.json').read_text())['returncode']==0,label
assert json.loads((b/'owned-analysis-fixture-validation.json').read_text())['status']=='passed'
summary=json.loads((b/'owned-analysis-fixture-tests.log').read_text());assert summary['completed_commands']==23727
q['full_validation']=summary
for name,digest in summary['inputs_sha256'].items():assert sha(root/name)==digest,name
for name,digest in json.loads((b/'common-controls-source/source.json').read_text())['files'].items():assert sha(root/name)==digest,name
source=json.loads((b/'owned-analysis-source/source.json').read_text())
for name,digest in source['files'].items():assert sha(root/name)==digest,name
build=json.loads((b/'owned-analysis-tools.json').read_text());baseline=json.loads((b/'current-baseline-tools.json').read_text())
for group in [build,baseline]:
 for name,digest in group['binaries'].items():assert sha(Path(group['directory'])/name)==digest,name
for name in ['rust-interp-vm','rust-interp-rustc-wrapper']:assert build['binaries'][name]==baseline['binaries'][name]
q['previous_unchanged_standalone_oracle']={'path':str(b/'local-layout-oracle-validation.json'),'sha256':sha(b/'local-layout-oracle-validation.json'),'inputs':261}
files=['owned-analysis-plan.md','owned-analysis-debug-tests.json','owned-analysis-debug-tests.log','owned-analysis-release-tests.json','owned-analysis-release-tests.log','owned-analysis-tools-build.json','owned-analysis-tools-build.log','owned-analysis-tools-install.json','owned-analysis-tools-install.log','owned-analysis-tools.json','owned-analysis-capabilities.json','owned-analysis-fixture-tests.json','owned-analysis-fixture-tests.log','owned-analysis-fixture-validation.json','install_owned_analysis.py','validate_owned_analysis.py','run_owned_analysis_screen.py','assess_owned_analysis_screen.py','qualify_owned_analysis.py','owned-analysis-source/source.json','common-controls-source/source.json','source-copies.json','std-mir-copy.json','owned-analysis.patch']
q['proofs']={str((b/n).relative_to(root)):sha(b/n) for n in files}
q['free_bytes_before_screen']=shutil.disk_usage(root).free
with (b/'owned-analysis-pre-screen-qualification.json').open('x') as f:json.dump(q,f,indent=2);f.write('\n')
print(json.dumps({'tests':q['tests'],'full_validation_commands':summary['completed_commands'],'tool_key':build['tool_key'],'proofs':len(files),'free_gib':q['free_bytes_before_screen']/2**30},indent=2))

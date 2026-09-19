"""Source-only one-time derivation; no imports of target modules or executions."""
from pathlib import Path
import ast,difflib,hashlib,json,re
R=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
RI=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
OLD=R/'experiments/runtime-installation-controls-07'
H=R/'experiments/runtime-installation-controls-08'
S=R/'experiments/runtime-installation-after-preflight05-03'
N=R/'experiments/runtime-native-loader-probes-01'
D=A/'.work/runtime-installation-controls08-source-derivation-01'
assert not H.exists() and not D.exists()
H.mkdir();D.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def change(s):
 s=re.sub(r'runtime-installation-controls([a-z-]*)-07',r'runtime-installation-controls\1-08',s)
 s=re.sub(r'runtime_installation_controls([a-z_]*)_07',r'runtime_installation_controls\1_08',s)
 s=s.replace('runtime-installation-after-preflight05-02','runtime-installation-after-preflight05-03')
 return s
sources={}
def write(old,new,text):
 ast.parse(text,filename=str(new))
 with new.open('x') as f:f.write(text)
 diff=''.join(difflib.unified_diff(old.read_text().splitlines(True),text.splitlines(True),fromfile=str(old),tofile=str(new)))
 (D/(new.name+'.from-passed07.diff')).write_text(diff)
 sources[str(new)]={'sha256':sha(new),'bytes':new.stat().st_size,'predecessor':str(old),'predecessor_sha256':sha(old),'diff':str(D/(new.name+'.from-passed07.diff'))}
source_names=['entry.py','controller.py','audit_owner.py','routes.json','prepare.py','prepare_once.py','launch.py','imports.py','test_installation.py','test_imports.py']
native_names=['runtime_compiler.py','producer_recipe.py','audit_recipe.py','test_native_loader.py']
extra=[RI/'scripts/runtime_compiler.py',RI/'scripts/custom_compiler.py',X/'experiments/hir-options-hash/runtime-installation-01/recipe.py',R/'experiments/runtime-installation-after-preflight05-02/installation-plan-01/specification.json']
base=[S/n for n in source_names]+[N/n for n in native_names]+extra+[R/'experiments/runtime04-environment-adapter-01/environment.py',R/'experiments/runtime-preflight-retry-05/routes.json']
devs=[('installation_factory',R/'results/runtime-installation07-test-development-02',S,30),('native_loader',R/'results/runtime-native-loader-development-01',N,18)]
declarations=[];development_paths=[]
for label,d,cwd,count in devs:
 manifest=json.loads((d/'manifest.json').read_bytes());assert len(manifest)==9 and 'manifest.json' not in manifest
 for name,row in manifest.items():
  assert set(row)=={'bytes','sha256'} and sha(d/name)==row['sha256'] and (d/name).stat().st_size==row['bytes']
 declarations.append((label,str(d),str(cwd),count,sha(d/'manifest.json'),sha(d/'result.json'),sha(d/'record.json')))
 development_paths.extend(d/name for name in [*manifest,'manifest.json'])
# Preserve all process/lock/output behavior; only route and source-derived count change.
s=change((OLD/'run.py').read_text());s=re.sub(r'\b25\b','48',s)
write(OLD/'run.py',H/'run.py',s)
s=change((OLD/'child.py').read_text());s=re.sub(r'\b25\b','48',s)
s=s.replace("MODULES = ['test_installation']","NATIVE = OWNER / 'experiments/runtime-native-loader-probes-01'\nMODULES = ['test_installation', 'test_native_loader', 'test_imports']")
s=s.replace("    sys.path.insert(0, str(SOURCE))","    sys.path.insert(0, str(NATIVE))\n    sys.path.insert(0, str(SOURCE))")
write(OLD/'child.py',H/'child.py',s)
s=change((OLD/'prepare.py').read_text());s=re.sub(r'\b25\b','48',s)
s=s.replace("    modules = ['test_installation']\n    for module in modules:\n        tree = ast.parse((source / (module + '.py')).read_text())", "    native = owner/'experiments/runtime-native-loader-probes-01'\n    modules = [('test_installation',source),('test_native_loader',native),('test_imports',source)]\n    for module, directory in modules:\n        tree = ast.parse((directory / (module + '.py')).read_text())")
s=s.replace("    for name in ['entry.py', 'controller.py', 'audit_owner.py', 'routes.json', 'prepare.py', 'prepare_once.py', 'launch.py', 'test_installation.py']:\n        add(source/name)", "    for name in "+repr(source_names)+":\n        add(source/name)\n    for name in "+repr(native_names)+":\n        add(native/name)\n    for path in "+repr([str(p) for p in extra])+":\n        add(path)")
a=s.index('    # Retain the completed ordinary development pass');b=s.index('    python = Path(sys.executable)',a)
block='''    # Two ordinary passes are retained as provenance, separately from this
    # future combined controlled execution. Their original manifests are finite
    # subsets; later publication/readback notes outside them are not implied.
    development_reference={}
    for label, directory, expected_cwd, count, manifest_sha, result_sha, record_sha in DECLARATIONS:
        development=Path(directory)
        assert control.owned.sha(development/'manifest.json')==manifest_sha
        manifest=control.read(development/'manifest.json')
        assert len(manifest)==9 and 'manifest.json' not in manifest
        for name,row in manifest.items():
            assert Path(name).name==name and set(row)=={'bytes','sha256'}
            path=development/name
            assert path.stat().st_size==row['bytes'] and control.owned.sha(path)==row['sha256']
            add(path)
        add(development/'manifest.json')
        ordinary=control.read(development/'result.json');closed=control.read(development/'record.json')
        before=control.read(development/'source-before.json')
        assert before==control.read(development/'source-after.json')
        assert ordinary['status']=='passed' and ordinary['actual_tests']==count
        assert ordinary['controlled_qualification'] is False and ordinary['sources_unchanged'] is True
        assert ordinary['record_sha256']==record_sha==control.owned.sha(development/'record.json')
        assert control.owned.sha(development/'result.json')==result_sha
        assert closed['status']=='closed' and closed['returncode']==0
        assert closed['cwd']==expected_cwd and closed['command']==['/opt/homebrew/bin/python3','-B',str(development/'child.py')]
        for stream in ['stdout','stderr']:
            assert closed[stream+'_sha256']==control.owned.sha(development/stream)
        for path,row in before.items():
            assert control.owned.sha(Path(path))==row['sha256']
            assert control.stamp(Path(path))==[row['identity'][k] for k in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
        development_reference[label]=dict(result=dict(path=str(development/'result.json'),sha256=result_sha),
            record=dict(path=str(development/'record.json'),sha256=record_sha),
            manifest=dict(path=str(development/'manifest.json'),sha256=manifest_sha))
'''.replace('DECLARATIONS',repr(declarations))
s=s[:a]+block+s[b:]
write(OLD/'prepare.py',H/'prepare.py',s)
# Preparation wrapper authenticates the exact current source/development inputs
# before its inherited helper import; original helper-auth source remains 05.
old=R/'.work/prepare_runtime_installation_controls_07_once.py';new=R/'.work/prepare_runtime_installation_controls_08_once.py'
s=change(old.read_text());s=s.replace('installation25_prepare_owned','installation48_prepare_owned')
expected={n:sha(H/n) for n in ['run.py','child.py','prepare.py']}
tested={str(p):sha(p) for p in base+[X/'experiments/stable-cgu/owned_stage.py']+development_paths}
s=re.sub(r'^EXPECTED = .*$', 'EXPECTED = '+repr(expected),s,flags=re.M)
s=re.sub(r'^TESTED = .*$', 'TESTED = '+repr(tested),s,flags=re.M)
write(old,new,s)
old=R/'.work/launch_runtime_installation_controls_07_bounded.py';new=R/'.work/launch_runtime_installation_controls_08_bounded.py'
s=change(old.read_text());s=re.sub(r'\b25\b','48',s);s=re.sub(r'^EXPECTED = .*$', 'EXPECTED = None',s,flags=re.M)
write(old,new,s)
old=R/'.work/verify_runtime_installation_controls_07.py';new=R/'.work/verify_runtime_installation_controls_08.py'
s=change(old.read_text());s=re.sub(r'\b25\b','48',s).replace('actual25','actual48')
for name in ['EXPECTED_LAUNCH','EXPECTED_INPUTS','EXPECTED_DISPATCHER','EXPECTED_INPUT_BYTES','EXPECTED_INPUT_FILES']:
 s=re.sub('^'+name+r' = .*$',name+' = None',s,flags=re.M)
a=s.index("development=A/'results/");b=s.index("assert l['launch_path']",a)
block='''reference=f['ordinary_development_reference']
expected_reference={}
for label,directory,expected_cwd,count,manifest_sha,result_sha,record_sha in DECLARATIONS:
 development=Path(directory)
 expected_reference[label]=dict(result=dict(path=str(development/'result.json'),sha256=result_sha),record=dict(path=str(development/'record.json'),sha256=record_sha),manifest=dict(path=str(development/'manifest.json'),sha256=manifest_sha))
 for row in expected_reference[label].values():assert sha(Path(row['path']))==row['sha256']==f['files'][row['path']]['sha256']
 ordinary=read(development/'result.json');ordinary_record=read(development/'record.json')
 assert ordinary['status']=='passed' and ordinary['actual_tests']==count and ordinary['controlled_qualification'] is False and ordinary['sources_unchanged'] is True
 assert ordinary['record_sha256']==record_sha and ordinary_record['status']=='closed' and ordinary_record['returncode']==0
 assert ordinary_record['cwd']==expected_cwd and ordinary_record['command']==['/opt/homebrew/bin/python3','-B',str(development/'child.py')]
 for stream in ['stdout','stderr']:assert ordinary_record[stream+'_sha256']==sha(development/stream)
 assert read(development/'source-before.json')==read(development/'source-after.json')
 manifest=read(development/'manifest.json');assert len(manifest)==9 and 'manifest.json' not in manifest
 for name,row in manifest.items():
  assert Path(name).name==name and set(row)=={'bytes','sha256'} and (development/name).stat().st_size==row['bytes'] and sha(development/name)==row['sha256']==f['files'][str(development/name)]['sha256']
assert reference==expected_reference
'''.replace('DECLARATIONS',repr(declarations))
s=s[:a]+block+s[b:]
s=s.replace("'test_installation.Preflight.test_':11}","'test_installation.Preflight.test_':11,'test_native_loader.NativeLoader.test_':18,'test_imports.Factory.test_':5}")
s=s.replace("Twenty-five pure installation16 route/phase/prerequisite controls with fixed-prefix budget subtests;7 route fixtures,7 phase/resource and separate-qualification fixtures,11 completed-preflight admission fixtures; history callback checks routing/refusal only; no compiler/provider/nested process calls and no actual runtime qualification", "Forty-eight pure controls: installation route/resource/prerequisite25, native-loader18, factory5 including520-row source-admission boundary subtests; actual saved admission JSON and selected AST bodies only; no provider/compiler/nested process calls or actual installation qualification")
write(old,new,s)
old=R/'.work/execute_runtime_installation_controls_audit_07.py';new=R/'.work/execute_runtime_installation_controls_audit_08.py'
s=change(old.read_text());s=re.sub(r'\b25\b','48',s).replace('actual25','actual48');s=re.sub(r'^EXPECTED = .*$', 'EXPECTED = None',s,flags=re.M)
write(old,new,s)
# Census from exact source paths/metadata only; do not import/run any preparer.
oldfreeze=json.loads((OLD/'inputs.json').read_bytes())
paths=[H/n for n in ['run.py','prepare.py','child.py']]+base+development_paths+[Path(oldfreeze['python']),Path('/opt/homebrew/bin/python3'),Path('/bin/ps'),Path('/usr/sbin/lsof'),R/'scripts/supervise_experiment.py',X/'experiments/stable-cgu/owned_stage.py']
rows={};routes={}
for p in paths:
 r=p.resolve(strict=True);routes[str(p)]=str(r);s=r.stat();rows[str(r)]={'size':s.st_size}
# Names are read from source AST, not imported tests.
names=[]
for p in [S/'test_installation.py',N/'test_native_loader.py',S/'test_imports.py']:
 tree=ast.parse(p.read_text())
 for node in tree.body:
  if isinstance(node,ast.ClassDef):names.extend(p.stem+'.'+node.name+'.'+child.name for child in node.body if isinstance(child,ast.FunctionDef) and child.name.startswith('test_'))
assert len(names)==len(set(names))==48
report={'status':'source-only-unrun','sources':sources,'expected_names':sorted(names),'count':48,'prospective_files':rows,'prospective_routes':routes,'prospective_file_count':len(rows),'prospective_route_count':len(routes),'prospective_bytes':sum(v['size'] for v in rows.values()),'development_declarations':declarations,'future_packet_pins':None,'target_imports':0,'tests_executed':0,'provider_calls':0}
(D/'handoff.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps({'handoff':str(D/'handoff.json'),'sha256':sha(D/'handoff.json'),'files':len(rows),'routes':len(routes),'bytes':report['prospective_bytes'],'sources':sources},indent=2))

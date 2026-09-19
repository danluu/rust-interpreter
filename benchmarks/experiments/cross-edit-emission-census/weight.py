"""Join closed original-anchor identities with the existing preparation trace."""
import importlib.util,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from associate import associate
RUN='cross-edit-emission-weight-01'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,12);frozen={}
    def bind(path,digest=None):
        actual=sha(path)
        if digest is not None:assert actual==digest,path
        frozen[str(path.relative_to(ROOT))]=actual
        return read(path) if path.suffix=='.json' else actual
    def closed(name):
        folder=ROOT/'results'/name;c=bind(folder/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        summary=bind(folder/'summary.json',c['summary_sha256'])
        bind(folder/'terminal.json',c['terminal_sha256'])
        return summary
    anchors=closed('cross-edit-emission-anchors-02');assert anchors['status']=='passed'
    raw_anchors=ROOT/anchors['raw']
    bind(raw_anchors/'plan.json',anchors['plan_sha256']);bind(raw_anchors/'records.json',anchors['records_sha256'])
    for path,digest in anchors['outputs'].items():bind(ROOT/path,digest)
    comparison=read(raw_anchors/'report.json');inputs=read(raw_anchors/'inputs.json')
    assert comparison['original_anchor'] is True and len(comparison['comparisons'])==7
    assert comparison['schema_version']==2
    identities=comparison['original_functions']
    assert [f['function'] for f in identities]==list(range(len(identities)))
    prior=closed('preparation-phase-workloads-refined-01');assert prior['status']=='passed' and prior['validator_controls']==8
    original=ROOT/prior['raw'];original_plan=bind(original/'plan.json',prior['plan_sha256'])
    original_records=bind(original/'records.json',prior['records_sha256'])
    command,=[r for r in original_records if r['label']=='pgrust-parser-original']
    assert command['returncode']==0
    artifact=Path(command['command'][-1]);assert sha(artifact)==inputs[0]['sha256']
    bind(artifact,inputs[0]['sha256'])
    profile_path=original/'pgrust-parser-original.json'
    profile=bind(profile_path,prior['outputs'][str(profile_path.relative_to(ROOT))])
    assert profile['passed']==114 and profile['failed']==0 and profile['workers']==2
    assert profile['mode']=='prepared' and profile['jit_code_limit_bytes']==16*1024*1024
    validator=ROOT/'benchmarks/experiments/preparation-phase-workloads/refined.py'
    bind(validator,original_plan['frozen'][str(validator.relative_to(ROOT))])
    spec=importlib.util.spec_from_file_location('retained_refined_validator',validator)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    totals=module.validate_observations(profile)
    assert totals==prior['observations'][0]['workers']
    for path in Path(__file__).parent.iterdir():
        if path.suffix in ['.py','.md']:bind(path)
    for name in ['compare_saved_runtime.py','workflow_io.py','suite_reports.py','native_suite.py']:bind(ROOT/'scripts'/name)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,expected_controls=4,
        original_project_guest_commands=0,performance_measurement=False,initial_minimum_gib=12))
    env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'};env['PYTHONDONTWRITEBYTECODE']='1';require_space(ROOT,8)
    child,out,err=capture([sys.executable,'-m','unittest','test_associate','-v'],cwd=Path(__file__).parent,env=env,
        receipt_path=raw/'active.json',receipt=dict(label='controls'))
    (raw/'controls.stdout').write_text(out);(raw/'controls.stderr').write_text(err)
    write(raw/'records.json',[dict(label='controls',pid=child.pid,returncode=child.returncode,
        stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))])
    assert child.returncode==0 and 'Ran 4 tests in ' in err and err.rstrip().endswith('OK'),err
    rows=[]
    for row in comparison['comparisons']:
        assert row['previous_artifact_sha256']==inputs[0]['sha256'] and row['previous_state']==0
        for f in row['functions']:
            identity=identities[f['function']]
            f.update(previous_name=identity['name'],previous_operations=identity['operations'],previous_sha256=identity['sha256'])
        rows.append(dict(state=row['state'],artifact_sha256=row['artifact_sha256'],
            workers=associate(row,profile['preparation_observations']['workers'])))
    assert [r['state'] for r in rows]==[-1,1,2,3,4,5,0]
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    output=ROOT/'results'/RUN;output.mkdir(exist_ok=False)
    write(output/'summary.json',dict(status='passed',source_revision=revision,commands=1,controls=4,
        original_artifact_sha256=inputs[0]['sha256'],rows=rows,original_project_guest_commands=0,
        performance_measurement=False,cache_admission=False,raw=str(raw.relative_to(ROOT)),
        scope='Association with one original diagnostic capture, not measurements of edited runs. Worker intervals overlap and phases nest. No-entry functions are excluded from native-template candidates. No estimated savings.',
        plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
    for row in rows:
        print(row['state'],json.dumps(row['workers'],sort_keys=True),flush=True)

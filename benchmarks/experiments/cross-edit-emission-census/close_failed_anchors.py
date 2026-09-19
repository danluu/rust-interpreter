"""Close the bounded anchor-report failure before changing its representation."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    name='cross-edit-emission-anchors-01';raw=ROOT/'.work'/name;outer=ROOT/'.work/experiments'/name
    plan=read(raw/'plan.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==str(ROOT)
    assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
    assert len(records)==1 and records[0]['returncode']==101
    assert 'assertion failed: bytes.len() <= 64 * 1024 * 1024' in (raw/'observe.stdout').read_text()
    assert not (raw/'report.json').exists()
    bindings={};evidence={}
    for path,digest in plan['frozen'].items():
        assert sha(ROOT/path)==digest,path
        if path.startswith(('.work/','results/')):evidence[path]=digest
        else:
            assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)).hexdigest()==digest
            bindings[path]=dict(revision=plan['source_revision'],sha256=digest)
    for stream in ['stdout','stderr']:
        p=raw/('observe.'+stream);assert sha(p)==records[0][stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
    assert sha(raw/'inputs.json')==plan['inputs_sha256']
    for p in [raw/'plan.json',raw/'records.json',raw/'inputs.json',outer/'plan.json',outer/'status.json',outer/'command.log']:
        evidence[str(p.relative_to(ROOT))]=sha(p)
    out=ROOT/'results'/name;out.mkdir(exist_ok=False)
    write(out/'summary.json',dict(status='diagnostic-failed',reason='Repeated function metadata exceeded64MiB report bound.',
        source_revision=plan['source_revision'],commands=1,returncodes=[101],original_project_guest_commands=0,
        executable_code_publications=0,report_published=False,raw=str(raw.relative_to(ROOT)),
        plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
    write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),
        frozen_inputs=len(plan['frozen']),evidence_files=len(evidence),
        source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),source_bindings_sha256=sha(raw/'source-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed report-bound failure; no report or executable publication',flush=True)

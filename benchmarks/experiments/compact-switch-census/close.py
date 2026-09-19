import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
def read(p):return json.loads(p.read_text())
RUN='compact-switch-census-01'
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN;s=read(out/'summary.json');t=read(outer/'status.json')
    assert s['status']=='passed' and not s['performance_measurement'] and s['guest_commands']==0
    assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert sha(ROOT/s['evidence'])==s['evidence_sha256']
    for path,h in read(ROOT/s['evidence']).items():assert sha(ROOT/path)==h
    for p in Path(__file__).parent.iterdir():
        if p.suffix in ['.py','.md']:assert hashlib.sha256(subprocess.check_output(['git','show',s['source_revision']+':'+str(p.relative_to(ROOT))],cwd=ROOT)).hexdigest()==sha(p)
    for c in s['cases']:
        assert sum(c['samples_by_shape'].values())==c['switch_samples']==sum(r['samples'] for r in c['sites'])
        assert sum(c['native_spans_by_shape'].values())==len(c['static_sites'])
        assert sum(c['native_words_by_shape'].values())==sum(r['words'] for r in c['static_sites'])
    assert not (out/'closure.json').exists()
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,summary_sha256=sha(out/'summary.json'),
        terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
    print('Closed saved switch-site census; no new guest, build or profile')

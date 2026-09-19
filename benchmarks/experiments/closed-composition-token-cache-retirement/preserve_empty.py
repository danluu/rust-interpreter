"""Preserve an empty retired-cache audit; never delete or retry it."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='closed-composition-token-cache-retirement-01'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN;t=read(outer/'status.json')
    assert t['status']=='finished' and t['returncode']==1 and t['owner']==t['cwd']==str(ROOT)
    assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
    assert 'no eligible compiler intermediates remain; no deletion attempted' in (outer/'command.log').read_text()
    assert read(raw/'inventory.json')==[] and not (raw/'plan.json').exists() and not (raw/'summary.json').exists()
    protected=read(raw/'protected.json');assert all(sha(ROOT/p)==h for p,h in protected.items())
    out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
    write(out/'summary.json',dict(status='empty-audit',files_removed=0,protected_files=len(protected),all_protected_hashes_unchanged=True,
        inventory_sha256=sha(raw/'inventory.json'),protected_sha256=sha(raw/'protected.json'),raw=str(raw.relative_to(ROOT)),
        reason='All seven exact namespaces already lack eligible compiler intermediates. Nothing deleted; do not repeat.',performance_measurement=False))
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',source_revision='f32710bf',files_removed=0,all_protected_hashes_unchanged=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Closed empty audit; zero removals;',len(protected),'protected hashes unchanged',flush=True)

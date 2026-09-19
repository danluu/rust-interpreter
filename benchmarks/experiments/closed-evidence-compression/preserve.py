"""Preserve a fixture setup failure before any copy or compression command."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
RUN='closed-evidence-compression-probe-01'
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45);require_space(ROOT,8)
    raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN;plan=read(raw/'plan.json');terminal=read(outer/'status.json')
    assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
    assert terminal['command'][1:]==plan['controller_command'][1:]
    assert terminal['plan_sha256']==sha(outer/'plan.json') and terminal['log_sha256']==sha(outer/'command.log')
    assert (outer/'command.log').read_text().endswith("AttributeError: module 'os' has no attribute 'setxattr'\n")
    assert read(raw/'records.json')==[] and not (raw/'active.json').exists()
    assert sorted(p.name for p in raw.iterdir())==['plan.json','records.json','repetitive.original']
    line=b'{"function":42,"operation":"load","frame":512,"counter":12345678,"source":"synthetic"}\n'
    assert (raw/'repetitive.original').read_bytes()==line*32768
    bindings={};evidence={}
    for name,h in plan['frozen'].items():
        assert sha(ROOT/name)==h
        assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+name],cwd=ROOT)).hexdigest()==h
        bindings[name]=dict(revision=plan['source_revision'],sha256=h)
    for p in [*raw.iterdir(),outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
    write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
    out=ROOT/'results'/RUN;out.mkdir(exist_ok=False);(out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'summary.json',dict(status='fixture-setup-failed',reason='This Python build lacks os.setxattr; stopped before copying or compression.',
        source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),commands=0,existing_files_modified=0,
        original_project_guest_commands=0,performance_measurement=False,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,existing_files_modified=0,no_copy_or_compression_executed=True,
        summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
        bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
        evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
    print('Closed fixture API failure; zero copy/compression commands and no existing files modified')

"""Archive the zero-command name-check rejection using its qualified sources."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
with (ROOT/'.work/benchmark.lock').open('a') as lock:
    acquire_lock(lock,45)
    name='native-continuation-snapshot-screen-token-01'
    outer=ROOT/'.work/experiments'/name;status=read(outer/'status.json')
    assert status['owner']==str(ROOT) and status['status']=='finished' and status['returncode']==1
    assert sha(outer/'command.log')==status['log_sha256'] and sha(outer/'plan.json')==status['plan_sha256']
    assert not (ROOT/'.work'/name).exists()
    log=(outer/'command.log').read_text()
    assert "assert '-continuation-' not in args.run_id, 'fresh screen required'" in log
    assert log.rstrip().endswith('AssertionError: fresh screen required')
    proof=ROOT/'results/native-continuation-snapshot-screen-protocol-01'
    closed=read(proof/'closure.json');summary=read(proof/'summary.json')
    assert closed['status']=='closed' and closed['all_hashes_verified']
    assert sha(proof/'summary.json')==closed['summary_sha256']
    inputs=ROOT/summary['raw']/'inputs.json';assert sha(inputs)==summary['inputs_sha256']
    revision='5ed1f431';path='benchmarks/experiments/native-continuation-snapshot-screen/screen.py'
    data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
    digest=hashlib.sha256(data).hexdigest();assert digest==read(inputs)[path]
    source=data.decode();assert source.index("assert '-continuation-' not in args.run_id")<source.index("with (ROOT / '.work/benchmark.lock')")
    out=ROOT/'results'/name;out.mkdir(exist_ok=False)
    evidence=[outer/n for n in ['status.json','plan.json','command.log']]+[inputs,proof/'summary.json',proof/'closure.json']
    write(out/'summary.json',dict(status='preflight_failed',reason='experiment name matched inherited continuation substring rejection',
        source_revision=revision,source_path=path,source_sha256=digest,benchmark_commands=0,performance_measurement=False,
        raw_work_directory_absent=True,evidence={str(p.relative_to(ROOT)):sha(p) for p in evidence}))
    (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
    write(out/'closure.json',dict(status='closed',all_hashes_verified=True,summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json')))
    print('Archived preflight rejection; no benchmark commands or raw work directory')

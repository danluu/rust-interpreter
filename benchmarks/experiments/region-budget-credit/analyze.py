"""Frozen saved-evidence budget-credit model and independent closure."""
from collections import Counter
import gc,hashlib,json,os,subprocess,sys
from pathlib import Path
from scope import case
import re,struct
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scratch-memory-values'))
from native_observation import logical_counts
RUN='region-budget-credit-01';LOOPS='adopted-hot-loop-census-02';CONTROLS=12
def read(p):
    assert p.stat().st_size<=256*1024**2
    return json.loads(p.read_text())
def rel(p):return str(p.relative_to(ROOT))
def inputs():
    frozen={}
    def bind(p,expected=None):
        h=sha(p)
        if expected is not None:assert h==expected,p
        frozen[rel(p)]=h
        return read(p) if p.suffix=='.json' else h
    out=ROOT/'results'/LOOPS;c=bind(out/'closure.json')
    assert c['status']=='closed' and c['all_hashes_verified'] and c['all_derivations_recomputed']
    s=bind(out/'summary.json',c['summary_sha256'])
    t=bind(out/'terminal.json',c['terminal_sha256'])
    assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0
    bindings=bind(ROOT/c['bindings'],c['bindings_sha256'])
    for p,row in bindings.items():bind(ROOT/p,row['sha256'])
    for label,h in s['details_sha256'].items():bind(ROOT/s['raw']/(label+'-details.json'),h)
    for p in HERE.iterdir():
        if p.suffix in ['.py','.md']:bind(p)
    for name in ['workflow_io.py','compare_saved_runtime.py','supervise_experiment.py']:bind(ROOT/'scripts'/name)
    bind(ROOT/'benchmarks/experiments/scratch-memory-values/native_observation.py')
    bind(ROOT/'benchmarks/experiments/adopted-hot-loop-census-v2/graph.py')
    return frozen


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen=inputs();revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(source_revision=revision,owner=str(ROOT),frozen=frozen,controls=CONTROLS,
            guest_commands=0,host_builds=0,production_changes=0,performance_measurement=False))
        require_space(ROOT,8)
        child,stdout,stderr=capture([sys.executable,'-m','unittest','test_model','-v'],cwd=HERE,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(stage='model controls'))
        (raw/'controls.stdout').write_text(stdout);(raw/'controls.stderr').write_text(stderr)
        write(raw/'records.json',[dict(pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr'))])
        assert child.returncode==0 and f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK'),stderr
        cases=[];detail_hashes={}
        for index,label in enumerate(['block','exhaustive']):
            s,rows=case(index,label);cases.append(s)
            write(raw/(label+'-details.json'),rows);detail_hashes[label]=sha(raw/(label+'-details.json'))
            print(json.dumps({k:v for k,v in s.items() if k not in ['top_sites','top_functions']}),flush=True)
            del rows;gc.collect()
        assert frozen==inputs()
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',raw=rel(raw),source_revision=revision,controls=CONTROLS,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),details_sha256=detail_hashes,
            cases=cases,guest_commands=0,host_builds=0,production_changes=0,performance_measurement=False,
            limitation='Abstract forward-edge budget credit and exact existing CMP/B.LO sample coverage. Potential entry-dependent samples are not removed time. No sampled edge history, machine-code proof, guest execution or performance measurement. Whole-test logical flow bounds and nominal word deltas remain separate; larger guards can change short-budget fallback paths. Native fault cursor publication is not modeled.'))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        out=ROOT/'results'/RUN;s=read(out/'summary.json');raw=ROOT/s['raw']
        assert s['status']=='passed' and s['controls']==CONTROLS
        for key in ['plan','records']:assert sha(raw/(key+'.json'))==s[key+'_sha256']
        plan=read(raw/'plan.json');assert plan['frozen']==inputs()
        bindings={}
        for p,h in plan['frozen'].items():
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        record,=read(raw/'records.json');assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/('controls.'+stream))==record[stream+'_sha256']
        stderr=(raw/'controls.stderr').read_text();assert f'Ran {CONTROLS} tests' in stderr and stderr.rstrip().endswith('OK')
        for index,label in enumerate(['block','exhaustive']):
            assert sha(raw/(label+'-details.json'))==s['details_sha256'][label]
            summary,rows=case(index,label)
            assert summary==s['cases'][index] and rows==read(raw/(label+'-details.json'))
            del rows;gc.collect()
        outer=ROOT/'.work/experiments'/RUN;t=read(outer/'status.json')
        assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
        assert Path(t['command'][0]).resolve()==Path(sys.executable).resolve()
        assert t['command'][1:]==[str(HERE/'analyze.py'),'--run-id',RUN]
        assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
        assert not (out/'closure.json').exists()
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes());write(raw/'bindings.json',bindings)
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,all_derivations_recomputed=True,
            source_revision=plan['source_revision'],frozen_inputs=len(bindings),bindings=rel(raw/'bindings.json'),
            bindings_sha256=sha(raw/'bindings.json'),summary_sha256=sha(out/'summary.json'),
            terminal_sha256=sha(out/'terminal.json'),guest_commands=0,performance_measurement=False))
        print('CLOSED',len(bindings),'bindings and both derivations',flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--close',action='store_true')
    args=parser.parse_args()
    assert re.fullmatch(r'region-budget-credit-[0-9]{2}',args.run_id)
    RUN=args.run_id
    if args.close:close()
    else:main()

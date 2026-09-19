"""Retain exact parser accounting evidence and qualify composed option bindings."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from prerequisites import components
from strict_probe_evidence import verified_paths
RUN='compact-native-switch-parser-protocol-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        old_result=ROOT/'results/cross-program-template-parser-full-protocol-02';c=bind(old_result/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        previous=bind(old_result/'summary.json',c['summary_sha256']);terminal=bind(old_result/'terminal.json',c['terminal_sha256'])
        assert previous['status']=='passed' and previous['tests']==8 and terminal['returncode']==0
        old=ROOT/previous['raw'];old_plan=bind(old/'plan.json',previous['plan_sha256']);old_records=bind(old/'records.json',previous['records_sha256'])
        assert len(old_records)==1 and old_records[0]['label']=='accounting' and old_records[0]['returncode']==0
        for name,h in old_plan['frozen'].items():bind(ROOT/name,h)
        for stream in ['stdout','stderr']:bind(old/('accounting.'+stream),old_records[0][stream+'_sha256'])
        for name in ['accounting.py','test_accounting.py']:
            assert sha(Path(__file__).parent/name)==sha(ROOT/'benchmarks/experiments/cross-program-template-full-parser'/name)
        base,candidate,paths=components();paths+=verified_paths()
        for p in paths:bind(p)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
                ROOT/'benchmarks/experiments/cross-program-template-screen/session_owner.py',
                ROOT/'benchmarks/experiments/runtime-composition-screen/screen.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=2,new_commands=1,reused_commands=1,
            original_project_guest_commands=0,performance_measurement=False,read_only_component_admission=True))
        records=[dict(old_records[0],reused_from=str((old/'records.json').relative_to(ROOT)))]
        for stream in ['stdout','stderr']:(raw/('accounting.'+stream)).write_bytes((old/('accounting.'+stream)).read_bytes())
        write(raw/'records.json',records)
        for label,count in [('commands',6)]:
            require_space(ROOT,8)
            command=[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_'+label+'.py','-v']
            start=time.time();child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,seconds=time.time()-start,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0 and f'Ran {count} tests in ' in err and '\nOK\n' in err,(out+err)[-5000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,count,'passed',flush=True)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=14,reused_tests=8,new_tests=6,
            commands=1,reused_commands=1,validated_commands=2,original_project_guest_commands=0,
            candidate_key=candidate['tool_key'],performance_measurement=False,default_runtime_adoption=False,portable_probe_source_verified=True,portable_probe_proof='compact-native-switch-guard-protocol-02'))
if __name__=='__main__':
    if sys.argv[1:]==['--close']:focus.RUN=RUN;focus.close()
    else:assert len(sys.argv)==1;main()

import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='composed-native-attribution-protocol-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest;return read(p)
        parent=ROOT/'.work/composed-fre-runtime-sampling-01';plan=bind(parent/'plan.json')
        for p,h in plan['frozen'].items():assert sha(ROOT/p)==h;frozen[p]=h
        failed=ROOT/'.work/experiments/composed-fre-runtime-sampling-01-analyze';terminal=bind(failed/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==1 and terminal['owner']==terminal['cwd']==str(ROOT)
        bind(failed/'plan.json',terminal['plan_sha256']);assert sha(failed/'command.log')==terminal['log_sha256'];frozen[str((failed/'command.log').relative_to(ROOT))]=terminal['log_sha256']
        assert "assert row['kind'] in" in (failed/'command.log').read_text()
        prior=bind(parent/'analysis-records.json');assert len(prior)==1 and prior[0]['label']=='block' and prior[0]['returncode']==0
        for stream in ['stdout','stderr']:
            p=parent/('block.'+stream);assert sha(p)==prior[0][stream+'_sha256'];frozen[str(p.relative_to(ROOT))]=sha(p)
        bind(ROOT/'results/composed-fre-sample-block-01/summary.json')
        assert not (ROOT/'results/composed-fre-sample-block-01/operation-attribution.json').exists()
        for case in plan['cases']:
            outer=ROOT/'.work/experiments'/case['run_id'];t=bind(outer/'status.json')
            assert t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
            bind(outer/'plan.json',t['plan_sha256']);assert sha(outer/'command.log')==t['log_sha256'];frozen[str((outer/'command.log').relative_to(ROOT))]=t['log_sha256']
            raw=ROOT/'.work'/case['run_id'];records=bind(raw/'records.json');record,=records
            bind(raw/'plan.json');bind(raw/'summary.json')
            for p,h in record['files'].items():assert sha(raw/'0'/p)==h;frozen[str((raw/'0'/p).relative_to(ROOT))]=h
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md')]:frozen[str(p.relative_to(ROOT))]=sha(p)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        specs=[dict(label='controls',command=[sys.executable,'-B','-m','unittest','test_composed_native_observation','-v'],cwd=str(Path(__file__).parent)),
            dict(label='retained',command=[sys.executable,'-B',str(Path(__file__).with_name('replay.py'))],cwd=str(ROOT))]
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,commands=specs,controller_command=[sys.executable,*sys.orig_argv[1:]],new_guest_commands=0))
        records=[];write(raw/'records.json',records)
        for spec in specs:
            require_space(ROOT,8);label=spec['label'];child,out,err=capture(spec['command'],cwd=spec['cwd'],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(**spec,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==0,(out+err)[-2000:]
            if label=='controls':assert 'Ran 5 tests' in err and err.rstrip().endswith('OK')
            else:assert json.loads(out)['status']=='passed' and len(json.loads(out)['cases'])==2
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=2,controls=5,
            captured_cases=read(raw/'retained.stdout')['cases'],new_guest_commands=0,failed_initial_analysis_retained=True,
            performance_measurement=False,plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
        print('Five controls and both retained composed captures validated; no guest rerun')
if __name__=='__main__':main()

"""Close exact original-test profile evidence without rerunning any guest."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import write_json as write

def read(p):return json.loads(p.read_text())
def main():
    run=sys.argv[1];assert run.startswith('confined-scalar-native-call-profile-') and Path(run).name==run
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        result=ROOT/'results'/run;summary=read(result/'summary.json');assert summary['status']=='passed' and summary['commands']==6
        work=ROOT/summary['raw'];plan=read(work/'plan.json');assert plan['owner']==str(ROOT)
        assert sha(work/'plan.json')==summary['plan_sha256'] and sha(work/'records.json')==summary['records_sha256']
        bindings={}
        for path,digest in plan['frozen'].items():
            assert sha(ROOT/path)==digest,path
            if path.startswith(('.work/','results/')):bindings[path]=dict(kind='retained',sha256=digest)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest,path
                bindings[path]=dict(kind='git',revision=plan['source_revision'],sha256=digest)
        records=read(work/'records.json');assert len(records)==6 and all(r['returncode']==0 for r in records)
        assert [(r['index'],r['mode']) for r in records]==[(i,m) for i in range(3) for m in ['control','candidate']]
        artifacts={}
        for row in summary['comparisons']:
            for key in ['profile','code','operations']:
                path=row[key+'_path'];assert sha(ROOT/path)==row[key+'_sha256'];artifacts[path]=row[key+'_sha256']
            mapping=(ROOT/row['code_path']).with_name('map.json');assert sha(mapping)==row['map_sha256'];artifacts[str(mapping.relative_to(ROOT))]=sha(mapping)
        for label in ['controls','launcher']:
            assert sha(work/(label+'.json'))==summary[('controls' if label=='controls' else 'launcher')+'_sha256']
            record=read(work/(label+'.json'));assert record['returncode']==0
            for stream in ['stdout','stderr']:
                p=work/(label+'.'+stream);assert sha(p)==record[stream+'_sha256'];artifacts[str(p.relative_to(ROOT))]=sha(p)
        outer=ROOT/'.work/experiments'/run;terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert not (result/'closure.json').exists()
        (result/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(result/'closure.json',dict(status='closed',summary_sha256=sha(result/'summary.json'),terminal_sha256=sha(result/'terminal.json'),
            frozen_inputs=bindings,artifacts=artifacts,all_hashes_verified=True,guest_commands=0,performance_measurement=False))
        print(run,len(bindings),'frozen inputs;',len(artifacts),'artifacts verified')
if __name__=='__main__':main()

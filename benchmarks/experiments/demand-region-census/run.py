"""Partition emitted ordinary regions using three exact adopted profiles."""
import hashlib,json,os,statistics,subprocess,sys
from pathlib import Path
from census import analyze
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from suite_reports import validate_report
RUN='demand-region-census-01'
ADOPTED='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        frozen={}
        def bind(p,expected=None):
            p=Path(p);h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h
            return read(p) if p.suffix=='.json' else h
        path=ROOT/'results/scratch-memory-values-profile-01/summary.json'
        closure=bind(path.with_name('closure.json'))
        assert closure['status']=='closed' and closure['all_hashes_verified']
        original=bind(path,closure['summary_sha256'])
        assert original['status']=='passed' and original['tool_key']==ADOPTED
        assert original['exact_logical_counts_memory_and_entropy'] and original['exact_per_pc_counts'] and original['exact_operation_map_reconstruction']
        old_bindings=bind(ROOT/closure['bindings'],closure['bindings_sha256'])
        for p,h in old_bindings['artifacts'].items():bind(ROOT/p,h)
        build=bind(ROOT/'results/scratch-memory-values-build-02/summary.json');assert build['tool_key']==ADOPTED
        build_plan=bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        for name in ['lib.rs','profile.rs','jit.rs','jit/resumable.rs','jit/values.rs']:
            path=ROOT/'crates/bytecode/src'/name;relative=str(path.relative_to(ROOT))
            bind(path,build_plan['frozen'][relative])
        for p in Path(__file__).parent.iterdir():
            if p.suffix in ['.py','.md']:bind(p)
        bind(ROOT/'benchmarks/experiments/native-continuation-snapshot-workflows/native_observation.py')
        for name in ['workflow_io.py','compare_saved_runtime.py']:bind(ROOT/'scripts'/name)
        prep_path=ROOT/'results/jit-preparation-census-01/summary.json'
        prep_closed=bind(prep_path.with_name('closure.json'));assert prep_closed['status']=='closed'
        bind(prep_path,prep_closed['summary_sha256'])
        inputs=[row for row in original['comparisons'] if row['mode']=='candidate']
        assert len(inputs)==3 and [r['index'] for r in inputs]==[0,1,2]
        for row in inputs:
            for key in ['profile','code','operations']:
                bind(ROOT/row[key+'_path'],row[key+'_sha256'])
            bind((ROOT/row['code_path']).with_name('map.json'),row['map_sha256'])
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        work=ROOT/'.work'/RUN;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,expected_observations=3,
            guest_commands=0,compiler_commands=0,executable_code_publications=0,performance_measurement=False))
        child,out,err=capture([sys.executable,'-m','unittest','test_census','-v'],cwd=Path(__file__).parent,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),receipt_path=work/'active.json',receipt=dict(stage='region census controls'))
        (work/'stdout').write_text(out);(work/'stderr').write_text(err)
        write(work/'record.json',dict(pid=child.pid,returncode=child.returncode,stdout_sha256=sha(work/'stdout'),stderr_sha256=sha(work/'stderr')))
        assert child.returncode==0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK'),err
        observations=[];details={}
        for label,row in zip(['block','exhaustive','folded'],inputs):
            require_space(ROOT,8)
            profile=read(ROOT/row['profile_path']);mapping=read((ROOT/row['code_path']).with_name('map.json'))
            operation_map=read(ROOT/row['operations_path'])
            assert operation_map['complete'] and operation_map['reconstructed_bytes_match']
            assert operation_map['code_sha256']==row['code_sha256']
            assert mapping['code_bytes']==operation_map['code_bytes']==(ROOT/row['code_path']).stat().st_size
            for key in ['pid','arena_base','profiled','persistent_registers','resumable_calls']:
                assert operation_map[key]==mapping[key]
            result=analyze(profile,mapping)
            assert result['logical_counts']==row['logical_counts']
            t=result['totals'];stats=row['statistics']
            assert t['all_bytes']==stats['jit_bytes'] and t['ordinary_functions']==stats['jit_compiled_functions']
            scalar_bytes=t.get('scalar_executed_bytes',0)+t.get('scalar_no_hits_bytes',0)
            assert scalar_bytes==row['scalar_code_bytes']
            observations.append(dict(case=label,totals=t,logical_counts=result['logical_counts'],
                recorded_profile_compile_ns=stats['jit_compile_ns'],
                top_no_work_functions=result['functions'][:15]))
            details[label]=dict(functions=result['functions'],regions=result['regions'])
            del profile,mapping,operation_map,result
            print(json.dumps(dict(case=label,totals=t)),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        write(work/'details.json',details)
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'observations.json',observations)
        write(result/'summary.json',dict(status='passed',tool_key=ADOPTED,observations=3,controls=6,
            raw=str(work.relative_to(ROOT)),source_revision=revision,plan_sha256=sha(work/'plan.json'),
            record_sha256=sha(work/'record.json'),observations_sha256=sha(result/'observations.json'),
            details_sha256=sha(work/'details.json'),
            guest_commands=0,compiler_commands=0,executable_code_publications=0,performance_measurement=False,
            scope='Exact profiled emitted-region/counter partition. Zero charged counts do not prove a region never entered; no execution order, retired instructions, preparation savings or speedup follows. Scalar bodies and interpreted work remain separate.'))


def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        result=ROOT/'results'/RUN;summary=read(result/'summary.json');raw=ROOT/summary['raw']
        assert summary['status']=='passed' and summary['observations']==3 and summary['controls']==6
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'record.json')==summary['record_sha256']
        assert sha(result/'observations.json')==summary['observations_sha256']
        assert sha(raw/'details.json')==summary['details_sha256']
        plan=read(raw/'plan.json');bindings={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):bindings[p]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h
                bindings[p]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        record=read(raw/'record.json');assert record['returncode']==0
        for stream in ['stdout','stderr']:assert sha(raw/stream)==record[stream+'_sha256']
        outer=ROOT/'.work/experiments'/RUN;terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        assert sha(outer/'command.log')==terminal['log_sha256']
        assert not (result/'closure.json').exists()
        (result/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(raw/'bindings.json',bindings)
        write(result/'closure.json',dict(status='closed',frozen_inputs=len(bindings),all_hashes_verified=True,
            bindings=str((raw/'bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'bindings.json'),
            summary_sha256=sha(result/'summary.json'),terminal_sha256=sha(result/'terminal.json')))
        print(len(bindings),'input bindings and all controls/observations verified')


if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()

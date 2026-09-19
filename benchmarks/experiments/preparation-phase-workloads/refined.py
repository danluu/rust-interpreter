"""Observe adopted preparation phases on exact original saved workload artifacts."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from suite_reports import validate_report,validate_runtime_limits
from workflow_io import capture,require_space,write_json as write
RUN='preparation-phase-workloads-refined-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
PHASES={'constructor','validation','jit_metadata','execution_metadata','compile_function','scalar_callees',
    'scalar_function','scalar_proof','scalar_lowering','scalar_emission','scalar_publication','ordinary_emission','ordinary_publication'}
ORDINARY={'ordinary_reads','ordinary_liveness','ordinary_fills','ordinary_call_slots','ordinary_layout','ordinary_regions','ordinary_relocations'}
PHASES |= ORDINARY
CONSTRUCTOR={'constructor','validation','jit_metadata','execution_metadata'}
SCALAR={'scalar_proof','scalar_lowering','scalar_emission','scalar_publication'}
def read(p):return json.loads(p.read_text())
def require(value,message):
    if not value:raise ValueError(message)
def integer(n):return type(n) is int and n>=0

def validate_observations(report):
    header=report.get('preparation_observations',{})
    require(header.get('schema_version')==1,'observation schema')
    workers=header.get('workers');require(isinstance(workers,list),'worker traces')
    require(type(report.get('workers')) is int and 1<=report['workers']<=2 and len(workers)==report['workers'],'worker count')
    require([w.get('worker') for w in workers]==list(range(report['workers'])),'worker identity')
    result=[]
    for worker in workers:
        require(worker.get('status')=='observed','diagnostic error')
        obs=worker['observation'];trace=obs['trace'];rows=trace['rows'];functions=obs['functions']
        require(trace.get('schema_version')==1 and trace.get('complete') is True and trace.get('overflowed') is False
                and type(trace.get('dropped_intervals')) is int and trace['dropped_intervals']==0,'incomplete trace')
        require(type(trace.get('bucket_limit')) is int and trace['bucket_limit']==65_536 and len(rows)<=65_536,'bucket bound')
        require(isinstance(functions,list) and all(isinstance(f,dict) for f in functions),'function metadata')
        ids=[f['function'] for f in functions]
        require(all(integer(i) for i in ids) and len(ids)==len(set(ids)),'function identity')
        by_id={f['function']:f for f in functions};buckets={};totals={p:0 for p in PHASES}
        for f in functions:
            require(isinstance(f.get('name'),str) and f['name'] and integer(f.get('bytecode_operations'))
                and f['bytecode_operations']>0 and type(f.get('ordinary_prepared')) is bool
                and integer(f.get('ordinary_native_entries')) and f['ordinary_native_entries']<=f['bytecode_operations']
                and integer(f.get('scalar_native_bytes')),'function fields')
        for row in rows:
            require(isinstance(row,list) and len(row)==3,'row shape');fid,phase,m=row
            require(phase in PHASES and ((phase in CONSTRUCTOR and fid is None) or
                (phase not in CONSTRUCTOR and integer(fid) and fid in by_id)),'phase or scope')
            require((fid,phase) not in buckets,'duplicate interval')
            require(isinstance(m,dict) and type(m.get('calls')) is int and m['calls']==1 and integer(m.get('nanos')),'once-per-owner count')
            buckets[fid,phase]=m['nanos'];totals[phase]+=m['nanos']
        require({i for i,p in buckets if i is not None}==set(ids),'unobserved function metadata')
        require(all((None,p) in buckets for p in CONSTRUCTOR),'constructor coverage')
        require(totals['constructor']>=sum(totals[p] for p in CONSTRUCTOR-{'constructor'}),'constructor nesting')
        for fid in ids:
            if (fid,'compile_function') in buckets:
                require(all((fid,p) in buckets for p in ['ordinary_emission','ordinary_publication','scalar_callees']),'compile coverage')
                require(buckets[fid,'compile_function']>=sum(buckets[fid,p] for p in ['ordinary_emission','ordinary_publication','scalar_callees']),'compile nesting')
            if any((fid,p) in buckets for p in ORDINARY):
                require((fid,'ordinary_emission') in buckets,'ordinary parent')
                require(all((fid,p) in buckets for p in ORDINARY-{'ordinary_relocations'}),'ordinary coverage')
                require(buckets[fid,'ordinary_emission']>=sum(buckets.get((fid,p),0) for p in ORDINARY),'ordinary nesting')
            if any((fid,p) in buckets for p in SCALAR):
                require((fid,'scalar_function') in buckets,'scalar parent')
                require(buckets[fid,'scalar_function']>=sum(buckets.get((fid,p),0) for p in SCALAR),'scalar nesting')
        require(all(integer(obs.get(p)) for p in ['compiled_functions','declined_functions','code_bytes']),'owner totals')
        ranked=[]
        for fid in ids:
            ns=buckets.get((fid,'compile_function'),0)
            if ns:
                ranked.append(dict(by_id[fid],compile_ns=ns,phases_ns={p:buckets[fid,p] for p in PHASES if (fid,p) in buckets}))
        ranked.sort(key=lambda f:f['compile_ns'],reverse=True)
        scalar_ranked=[dict(by_id[fid],scalar_function_ns=buckets[fid,'scalar_function'],
            phases_ns={p:buckets[fid,p] for p in SCALAR if (fid,p) in buckets}) for fid in ids if (fid,'scalar_function') in buckets]
        scalar_ranked.sort(key=lambda f:f['scalar_function_ns'],reverse=True)
        result.append(dict(worker=worker['worker'],phase_ns=totals,ordinary_unattributed_ns=totals['ordinary_emission']-sum(totals[p] for p in ORDINARY),buckets=len(rows),functions=len(ids),
            compiled_functions=obs['compiled_functions'],declined_functions=obs['declined_functions'],code_bytes=obs['code_bytes'],
            top_compile=ranked[:20],top_scalar=scalar_ranked[:20],
            prepared_without_entries=[f for f in ranked if f['ordinary_prepared'] and f['ordinary_native_entries']==0]))
    return result

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();frozen={}
        def bind(path,digest=None):
            path=Path(path);value=sha(path)
            if digest is not None:assert value==digest,path
            frozen[str(path.relative_to(ROOT))]=value
            return read(path) if path.suffix=='.json' else path
        def closed(run):
            folder=ROOT/'results'/run;c=bind(folder/'closure.json')
            assert c['status']=='closed' and (c.get('all_hashes_verified') or c.get('all_retained_artifacts_and_sources_verified'))
            return bind(folder/'summary.json',c['summary_sha256'])
        build=closed('preparation-phases-refined-01');assert build['status']=='passed' and build['tests_per_profile']==9
        build_raw=ROOT/build['raw'];source=bind(build_raw/'plan.json',build['plan_sha256']);bind(build_raw/'records.json',build['records_sha256'])
        for p,h in source['frozen'].items():
            if p.startswith('crates/') or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        binary,digest=next(iter(build['outputs'].items()));vm=bind(ROOT/binary,digest)
        def history(run,name,states,count):
            summary=closed(run);assert summary['status']=='passed' and summary['tool_keys']['baseline']==BASELINE
            raw=ROOT/summary['raw'];bind(raw/'plan.json',summary['plan_sha256']);records=bind(raw/'records.json',summary['records_sha256']);cases=[]
            for state in states:
                old=next(r for r in records if r['cycle']==0 and r['state']==state and r['mode']=='baseline')
                native=next(r for r in records if r['cycle']==0 and r['state']==state and r['mode']=='native')
                assert old['outcomes']==native['outcomes']
                artifact=bind(ROOT/old['artifact']['path'],old['artifact']['sha256'])
                c=old.get('entry_catalog') or old['catalog'];catalog=ROOT/c['path'];entry=bind(catalog,c['sha256'])
                names=[e['name'] for e in entry['entries']];assert len(names)==len(set(names))==count
                report=bind(Path(old['launch']['suite_report_path']),old['suite_sha256'])
                outcomes=validate_report(report,names,'prepared',state!=-1)
                assert [list(r) for r in outcomes]==old['outcomes'];validate_runtime_limits(report,100000000000,150000,required=True)
                cases.append(dict(name=name+('-wrong' if state==-1 else '-original'),artifact=artifact,catalog=catalog,
                    names=names,outcomes=outcomes,success=state!=-1))
            return cases
        cases=history('runtime-composition-parser-edits-incremental-01','pgrust-parser',[0],114)
        cases+=history('runtime-composition-edit-token-02','fre-token',[0],12)
        previous=closed('preparation-phase-workloads-01')
        assert previous['status']=='passed' and previous['cli_rejections']==6 and previous['original_project_guest_commands']==3
        previous_raw=ROOT/previous['raw'];bind(previous_raw/'plan.json',previous['plan_sha256']);bind(previous_raw/'records.json',previous['records_sha256'])
        # Admission/CLI code is byte-identical; refined instrumentation changes only JIT internals and phase declarations.
        for p,h in read(previous_raw/'plan.json')['frozen'].items():
            if p in ['crates/bytecode/src/main.rs','crates/bytecode/src/suite.rs','crates/bytecode/src/prepared.rs']:bind(ROOT/p,h)
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py','.md']:bind(path)
        for p in ['workflow_io.py','compare_saved_runtime.py','suite_reports.py','native_suite.py']:bind(ROOT/'scripts'/p)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controller_command=[sys.executable,*sys.orig_argv[1:]],
            vm_sha256=digest,expected_commands=3,original_project_guest_commands=2,cli_rejections=0,
            initial_minimum_gib=12,minimum_child_gib=8,maximum_report_bytes=64*1024*1024,workers=2,
            source_edits=0,performance_measurement=False,native_outcomes_reused=True,entropy='ordinary OS',
            scope='elapsed diagnostic preparation phases; nested intervals and overlapping workers are not additive or recoverable savings'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))};assert not any(k.startswith('DYLD_') for k in env)
        env['PYTHONDONTWRITEBYTECODE']='1';records=[];outputs={};observations=[]
        write(raw/'records.json',records);write(raw/'outputs.json',outputs)
        def invoke(label,command,expected,report_path=None):
            require_space(ROOT,8);command=list(map(str,command));start=time.time()
            child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,expected_returncode=expected,
                seconds=time.time()-start,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            if report_path is not None and report_path.exists():outputs[str(report_path.relative_to(ROOT))]=sha(report_path);write(raw/'outputs.json',outputs)
            assert child.returncode==expected,(label,err[-3000:])
            assert all(sha(ROOT/p)==h for p,h in frozen.items());return out,err
        out,err=invoke('validator-controls',[sys.executable,'-B',Path(__file__).with_name('test_refined.py')],0)
        assert 'Ran 8 tests in ' in err and '\nOK\n' in err
        for case in cases:
            label=case['name'];path=raw/(label+'.json')
            command=[vm,'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                '--isolated-batch','prepared','--suite-workers','2','--suite-report',path,'--suite-catalog',case['catalog'],
                '--instruction-limit','100000000000','--allocation-limit','150000',case['artifact']]
            out,err=invoke(label,command,0 if case['success'] else 1,path)
            assert not path.is_symlink() and 0<path.stat().st_size<=64*1024*1024
            report=read(path);assert validate_report(report,case['names'],'prepared',case['success'])==case['outcomes']
            validate_runtime_limits(report,100000000000,150000,required=True)
            assert report['requested_workers']==report['workers']==2 and out==('0\n' if case['success'] else '')
            workers=validate_observations(report)
            observations.append(dict(name=label,tests=len(case['names']),workers=workers,report_sha256=outputs[str(path.relative_to(ROOT))]))
            write(raw/'observations.json',observations);print(label,'observed',flush=True)
        assert len(records)==3
        outputs[str((raw/'observations.json').relative_to(ROOT))]=sha(raw/'observations.json');write(raw/'outputs.json',outputs)
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            commands=len(records),original_project_guest_commands=2,cli_rejections=0,validator_controls=8,vm_sha256=digest,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),outputs=outputs,
            observations=observations,reused_cli_controls='preparation-phase-workloads-01',source_edits=0,native_outcomes_match=True,performance_measurement=False))

def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;outer=ROOT/'.work/experiments'/RUN;out=ROOT/'results'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:] and Path(terminal['command'][0]).resolve()==Path(plan['controller_command'][0]).resolve()
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        evidence={};bindings={}
        for p,h in plan['frozen'].items():
            assert sha(ROOT/p)==h
            if p.startswith(('.work/','results/')):evidence[p]=h
            else:
                assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_revision']+':'+p],cwd=ROOT)).hexdigest()==h
                bindings[p]=dict(revision=plan['source_revision'],sha256=h)
        for record in records:
            for stream in ['stdout','stderr']:
                p=raw/(record['label']+'.'+stream);assert sha(p)==record[stream+'_sha256'];evidence[str(p.relative_to(ROOT))]=sha(p)
        for p,h in read(raw/'outputs.json').items():assert sha(ROOT/p)==h;evidence[p]=h
        if (raw/'observations.json').exists():evidence[str((raw/'observations.json').relative_to(ROOT))]=sha(raw/'observations.json')
        out.mkdir(exist_ok=True);assert not (out/'closure.json').exists()
        if terminal['returncode']==0:
            summary=read(out/'summary.json');assert summary['status']=='passed' and len(records)==3
            assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        else:
            assert not (out/'summary.json').exists()
            write(out/'summary.json',dict(status='observation-failed',source_revision=plan['source_revision'],raw=str(raw.relative_to(ROOT)),
                commands=len(records),returncodes=[r['returncode'] for r in records],plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),
                outputs=read(raw/'outputs.json'),performance_measurement=False))
        for p in [raw/'plan.json',raw/'records.json',raw/'outputs.json',outer/'status.json',outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        write(raw/'source-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,source_files=len(bindings),frozen_inputs=len(plan['frozen']),evidence_files=len(evidence),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),source_bindings=str((raw/'source-bindings.json').relative_to(ROOT)),
            source_bindings_sha256=sha(raw/'source-bindings.json'),evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json')))
        print('Closed original workload observations',terminal['returncode'],flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()

"""Qualify portable unreachable probes with the pinned real Rust front end."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from admission import load
from benchmark import strict_probes
RUN='session-runtime-composition-pgrust-protocol-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,14);frozen={}
        def bind(p,h=None):
            actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        failed=ROOT/'results/session-runtime-composition-edit-pgrust-01';c=bind(failed/'closure.json')
        assert c['status']=='closed' and c['no_guest_execution'] and c['no_timed_commands']
        failure=bind(failed/'summary.json',c['summary_sha256']);bind(failed/'terminal.json',c['terminal_sha256'])
        assert failure['commands']==failure['session_requests']==0 and failure['source_restored']
        old_result=ROOT/'results/session-runtime-composition-guard-protocol-01';c=bind(old_result/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        previous=bind(old_result/'summary.json',c['summary_sha256']);terminal=bind(old_result/'terminal.json',c['terminal_sha256'])
        assert previous['status']=='passed' and previous['tests']==22 and terminal['returncode']==0
        old=ROOT/previous['raw'];old_plan=bind(old/'plan.json',previous['plan_sha256']);old_records=bind(old/'records.json',previous['records_sha256'])
        for name,h in old_plan['frozen'].items():bind(ROOT/name,h)
        reused=[r for r in old_records if r['label'] in ['accounting','commands']]
        assert [r['label'] for r in reused]==['accounting','commands'] and all(r['returncode']==0 for r in reused)
        for r in reused:
            for stream in ['stdout','stderr']:bind(old/(r['label']+'.'+stream),r[stream+'_sha256'])
        for name in ['accounting.py','test_accounting.py','commands.py']:
            assert sha(Path(__file__).parent/name)==sha(ROOT/'benchmarks/experiments/session-runtime-composition-guards'/name)
        builds,paths=load('pgrust')
        for p in paths:bind(p)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__),
                ROOT/'benchmarks/experiments/cross-program-template-screen/session_owner.py',
                ROOT/'benchmarks/experiments/runtime-composition-screen/screen.py']:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);(raw/'metadata').mkdir()
        compiler=Path(subprocess.check_output(['rustup','which','--toolchain','nightly-2026-09-08','rustc'],text=True).strip()).resolve(strict=True)
        identity=dict(path=str(compiler),sha256=sha(compiler),version=subprocess.check_output([str(compiler),'-vV'],text=True))
        write(raw/'compiler.json',identity);frozen[str((raw/'compiler.json').relative_to(ROOT))]=sha(raw/'compiler.json')
        probes=[]
        for prefix in ['std','no_std']:
            for label,code,diagnostic in strict_probes():
                p=raw/(prefix+'-'+label+'.rs');p.write_bytes((b'#![no_std]\n' if prefix=='no_std' else b'')+code)
                frozen[str(p.relative_to(ROOT))]=sha(p)
                probes.append((prefix+'-'+label,[str(compiler),'--crate-type=lib','--crate-name','strict_probe','--edition=2024','--emit=metadata',str(p),'--out-dir',str(raw/'metadata')],diagnostic))
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,compiler=identity,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=7,new_commands=5,reused_commands=2,
            original_project_guest_commands=0,performance_measurement=False,small_compiler_probe_minimum_gib=14,shared_target_used=False))
        records=[dict(r,reused_from=str((old/'records.json').relative_to(ROOT))) for r in reused]
        for r in reused:
            for stream in ['stdout','stderr']:(raw/(r['label']+'.'+stream)).write_bytes((old/(r['label']+'.'+stream)).read_bytes())
        write(raw/'records.json',records)
        commands=[('controller',[sys.executable,'-B','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_controller.py','-v'],None),*probes]
        for label,command,diagnostic in commands:
            require_space(ROOT,8);assert sha(compiler)==identity['sha256']
            started=time.time();child,out,err=capture(command,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,expected_diagnostic=diagnostic,seconds=time.time()-started,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            if diagnostic:assert child.returncode==1 and diagnostic in err and 'E0433' not in err and not list((raw/'metadata').iterdir()),(out+err)[-4000:]
            else:assert child.returncode==0 and 'Ran 4 tests in ' in err and '\nOK\n' in err,(out+err)[-4000:]
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(label,'passed',flush=True)
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),tests=26,reused_tests=18,new_tests=8,
            commands=5,reused_commands=2,validated_commands=7,original_project_guest_commands=0,
            candidate_key=builds['candidate']['tool_key'],performance_measurement=False,default_runtime_adoption=False))
def close():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        raw=ROOT/'.work'/RUN;out=ROOT/'results'/RUN;outer=ROOT/'.work/experiments'/RUN
        plan=read(raw/'plan.json');records=read(raw/'records.json');summary=read(out/'summary.json');terminal=read(outer/'status.json')
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==terminal['cwd']==plan['owner']==str(ROOT)
        assert terminal['command'][1:]==plan['controller_command'][1:]
        assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
        assert summary['status']=='passed' and summary['tests']==26 and len(records)==plan['expected_commands']==7
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        compiler=read(raw/'compiler.json');assert compiler==plan['compiler'] and sha(Path(compiler['path']))==compiler['sha256']
        assert [r['label'] for r in records]==['accounting','commands','controller','std-type','std-borrow','no_std-type','no_std-borrow']
        assert [r['returncode'] for r in records]==[0,0,0,1,1,1,1]
        for row in records:
            for stream in ['stdout','stderr']:assert sha(raw/(row['label']+'.'+stream))==row[stream+'_sha256']
            diagnostic=row.get('expected_diagnostic')
            if diagnostic:
                err=(raw/(row['label']+'.stderr')).read_text();assert diagnostic in err and 'E0433' not in err
                assert row['command'][0]==compiler['path'] and '--emit=metadata' in row['command']
        assert not list((raw/'metadata').iterdir())
        bindings={};evidence={}
        for name,h in plan['frozen'].items():
            assert sha(ROOT/name)==h,name
            if name.startswith(('.work/','results/')):bindings[name]=dict(kind='retained',sha256=h)
            else:
                data=subprocess.check_output(['git','show',plan['source_revision']+':'+name],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==h,name
                bindings[name]=dict(kind='git',revision=plan['source_revision'],sha256=h)
        for p in raw.rglob('*'):
            if p.is_file():assert not p.is_symlink();evidence[str(p.relative_to(ROOT))]=sha(p)
        for p in [outer/'plan.json',outer/'status.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        assert not (out/'closure.json').exists();write(raw/'closed-bindings.json',bindings);write(raw/'closed-evidence.json',evidence)
        (out/'terminal.json').write_bytes((outer/'status.json').read_bytes())
        write(out/'closure.json',dict(status='closed',all_hashes_verified=True,frozen_inputs=len(bindings),evidence_files=len(evidence),
            summary_sha256=sha(out/'summary.json'),terminal_sha256=sha(out/'terminal.json'),
            bindings=str((raw/'closed-bindings.json').relative_to(ROOT)),bindings_sha256=sha(raw/'closed-bindings.json'),
            evidence=str((raw/'closed-evidence.json').relative_to(ROOT)),evidence_sha256=sha(raw/'closed-evidence.json'),
            compiler_sha256=compiler['sha256'],four_expected_compiler_rejections=True,no_code_or_metadata_emitted=True))
        print('Closed26 protocol controls including four actual std/no_std compiler rejections')
if __name__=='__main__':
    if sys.argv[1:]==['--close']:close()
    else:assert len(sys.argv)==1;main()

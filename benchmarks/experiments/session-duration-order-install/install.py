"""Compose closed runtime binaries with the byte-identical adopted compiler tools."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from interpreter import installed_tools
RUN='session-duration-order-install-01'
BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
def read(p):return json.loads(p.read_text())

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12);frozen={}
        def bind(p,expected=None):
            h=sha(p)
            if expected is not None:assert h==expected,p
            frozen[str(p.relative_to(ROOT))]=h;return read(p) if p.suffix=='.json' else h
        def closed(name):
            result=ROOT/'results'/name;c=bind(result/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
            t=bind(result/'terminal.json',c['terminal_sha256']);assert t['status']=='finished' and t['returncode']==0 and t['owner']==str(ROOT)
            s=bind(result/'summary.json',c['summary_sha256']);assert s['status']=='passed';return s
        qualification=closed('session-duration-order-qualification-01');replay=closed('session-duration-order-parser-client-01')
        assert qualification['large_function_interpreter_threshold']==replay['large_function_interpreter_threshold']==65536
        assert qualification['duration_order'] is True and qualification['shared_literal_keys'] is False
        assert qualification['parameterized_literals'] is replay['parameterized_literals'] is True
        assert qualification['buffered_template_keys'] is replay['buffered_template_keys'] is False
        assert qualification['artifact_digest_reuse'] is replay['artifact_digest_reuse'] is True
        assert qualification['template_key_domain']=='cross-program-staging-literals-v1'
        phases=closed('session-duration-order-phases-parser-01')
        assert phases['duration_order'] is replay['duration_order'] is True
        assert phases['shared_literal_keys'] is replay['shared_literal_keys'] is False
        assert phases['parameterized_literals'] is True and phases['test_invocations']==1824
        assert qualification['diagnostic_feature'] is replay['diagnostic_feature'] is False
        assert qualification['tests']['debug']==qualification['tests']['release']==dict(passed=679,ignored=17)
        assert qualification['tests']['python']==dict(discovered=464,passed=442,skipped=22)
        assert replay['test_invocations']==1824 and replay['verified_cache_hits']>0 and replay['kernel_cpu_reconciled']
        for s in [qualification,replay,phases]:
            plan=bind(ROOT/s['raw']/'plan.json',s['plan_sha256'])
            for p,h in plan['frozen'].items():
                if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        for p,h in qualification['outputs'].items():bind(ROOT/p,h)
        vm=ROOT/qualification['raw']/'release-rust-interp-vm';server=ROOT/qualification['raw']/'release-rust-interp-template-session'
        base=bind(ROOT/'results/scratch-scalar-main-qualification-01/summary.json');assert base['status']=='passed' and base['tool_key']==BASELINE
        retained,key=installed_tools(BASELINE);assert key==BASELINE
        for name,h in base['binaries'].items():bind(retained/name,h)
        for name in ['ready.json','source.json','capabilities.json']:bind(retained/name)
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),Path(focus.__file__)]:bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,original_project_guest_commands=0,
            source_builds=0,performance_measurement=False,default_runtime_adoption=False))
        write(raw/'records.json',[]);binaries=dict(base['binaries']);binaries['rust-interp-vm']=sha(vm)
        composition=dict(kind='duration-order-literal-immutable-artifact-digest-template-session',schema_version=1,source_commit=revision,
            runtime_source_commit=qualification['source_revision'],compiler_source_key=BASELINE,binaries=binaries,
            duration_order=True,shared_literal_keys=False,parameterized_literals=True,buffered_template_keys=False,artifact_digest_reuse=True,template_key_domain="cross-program-staging-literals-v1",large_function_interpreter_threshold=65536,diagnostic_feature=False,
            server_executable_sha256=sha(server),server_path=str(server),session_required_for_history=True,default_runtime_adoption=False)
        key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with (ROOT/'.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
            for name in binaries:shutil.copy2(vm if name=='rust-interp-vm' else retained/name,installed/name)
            caps=read(retained/'capabilities.json');caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed/'capabilities.json',caps)
            write(installed/'source.json',dict(tool_key=key,composition=composition,files=frozen,source_commit=revision,
                key_algorithm='SHA256 of canonical composition JSON',source=str(ROOT)))
            assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
        outputs={str((installed/n).relative_to(ROOT)):sha(installed/n) for n in [*binaries,'ready.json','source.json','capabilities.json']}
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        destination=ROOT/'results'/RUN;destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=0,
            tool_key=key,binaries=binaries,composition=composition,outputs=outputs,python=qualification['tests']['python'],
            rust=qualification['tests']['release'],original_project_guest_commands=0,default_runtime_adoption=False,performance_measurement=False))
        print('Installed experimental tool',key,flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()

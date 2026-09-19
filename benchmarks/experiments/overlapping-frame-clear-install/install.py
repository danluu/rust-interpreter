"""Compose the qualified overlapping-frame-clear VM with byte-identical adopted compiler tools."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cross-program-template-model'))
import focus
ROOT=focus.ROOT
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from interpreter import installed_tools
RUN='overlapping-frame-clear-install-01'
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
        qualification=closed('overlapping-frame-clear-workspace-01')
        replay=closed('overlapping-frame-clear-profile-01')
        focused=closed('overlapping-frame-clear-focused-01')
        assert qualification['tests']['debug']==qualification['tests']['release']==dict(passed=612,ignored=15)
        assert qualification['tests']['python']==dict(discovered=468,passed=446,skipped=22)
        assert focused['tests_per_profile']==10 and focused['commands']==2
        assert replay['commands']==10 and replay['original_project_guest_commands']==10 and replay['adopted_tool_key']==BASELINE
        for field in ['exact_per_pc_counts','exact_memory_and_entropy','exact_span_shrinkage']: assert replay[field] is True
        assert len(replay['comparisons'])==5
        assert qualification['runtime_diff_files']==['crates/bytecode/src/jit/'+p for p in ['resumable.rs','resumable_tests.rs']]
        for s in [qualification,replay,focused]:
            plan=bind(ROOT/s['raw']/'plan.json',s['plan_sha256'])
            for p,h in plan['frozen'].items():
                if p.startswith(('crates/','scripts/','tests/')) or p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']:bind(ROOT/p,h)
        for p,h in qualification['outputs'].items():bind(ROOT/p,h)
        vm=ROOT/qualification['raw']/'rust-interp-vm';assert sha(vm)==replay['vm_sha256']
        # This historical closure predates the common all_hashes_verified field.
        historical=ROOT/'results/scratch-memory-values-qualification-01'
        c=bind(historical/'closure.json');assert c['status']=='closed' and c['logs_verified'] is True
        frontend=bind(historical/'summary.json',c['summary_sha256'])
        terminal=bind(historical/'terminal.json',c['terminal_sha256'])
        assert terminal['status']=='finished' and terminal['returncode']==0 and terminal['owner']==str(ROOT)
        source_bindings=bind(ROOT/c['source_bindings'],c['source_bindings_sha256'])
        for path,record in source_bindings.items():
            if record['kind']=='retained':bind(ROOT/path,record['sha256'])
            else:
                assert record['kind']=='git'
                payload=subprocess.check_output(['git','show',record['revision']+':'+path],cwd=ROOT)
                assert hashlib.sha256(payload).hexdigest()==record['sha256']
        historical_raw=ROOT/frontend['raw']
        for name in ['plan','records','cache_reports']:
            bind(historical_raw/(name.replace('_','-')+'.json'),frontend[name+'_sha256'])
        assert frontend['tool_key']==BASELINE and frontend['commands']==121 and frontend['scalar_enabled_strict_cargo']
        assert frontend['automatic_cache_qualified'] and frontend['source_restored']
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
        composition=dict(kind='overlapping-frame-clear',schema_version=1,source_commit=revision,
            runtime_source_commit=qualification['source_revision'],adopted_runtime_source=qualification['adopted_runtime_source'],
            compiler_source_key=BASELINE,binaries=binaries,bounded_overlapping_ordinary_frame_clear=True,cargo_features=[],
            runtime_diff_files=qualification['runtime_diff_files'],experimental_template_session=False,
            diagnostic_feature=False,default_runtime_adoption=False)
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
            rust=qualification['tests']['release'],tests={'test-debug':612,'test-release':612},
            matched_control=dict(tool_key=BASELINE,binaries=base['binaries']),
            reused_frontend_qualification='scratch-memory-values-qualification-01',reused_frontend_commands=121,
            semantic_qualification='overlapping-frame-clear-profile-01',original_project_guest_commands=0,default_runtime_adoption=False,performance_measurement=False))
        print('Installed experimental tool',key,flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--close']:
        focus.RUN=RUN;focus.close()
    else:
        assert len(sys.argv)==1
        main()

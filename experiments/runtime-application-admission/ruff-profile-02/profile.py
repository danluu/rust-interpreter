#!/usr/bin/env python3
"""One off/on Ruff self-profile pair through the installed runtime composition."""
from collections import Counter
import hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_admission_v2 import RuntimeAdmission,OWNER,R_OWNER,read,validate_hir_flags
from run_ruff_diagnostic import provider
from profile_helpers import require,digest,selected_artifact,compiler_records,source_inventory
from workflow_cases import WORKFLOWS
from workflow_case_file import source_file
from workflow_io import SourceEdit
from interpreter import selected_entry_catalog
from suite_reports import read_report,validate_report,validate_runtime_limits
from cargo_timing_data import units_from_html,timeline
from workflow_controls import exporter_seconds
NAME='ruff-hir-self-profile-02'
SOURCE=R_OWNER/'.work/sources/ruff'
ORDER=[('prime','baseline'),('prime','candidate'),('edited','candidate'),('edited','baseline'),('restored','baseline'),('restored','candidate')]

def flags(mode):
    value='true' if mode=='candidate' else 'false'
    require(mode in ['baseline','candidate'],'profile mode')
    return ['-Zmir-opt-level=3','-Zhir-body-cache-capture='+value,'-Zhir-body-cache-reuse='+value,'-Zincremental-info=true']

def cargo_command(cargo,host):
    return [str(cargo),'check','--manifest-path',str(SOURCE/'Cargo.toml'),'--package','ruff_linter','--lib','--locked','--offline','--jobs','2','--message-format=json-render-diagnostics','--profile','test','--target',host,'--timings','-vv']

def vm_command(tools,out):
    return [str(tools/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--instruction-limit','1000000000','--allocation-limit','150000','--isolated-batch','prepared','--suite-workers','1','--suite-report',str(out/'suite.json'),'--suite-catalog',str(out/'program.rbc.entries.json'),str(out/'program.rbc')]

def environment(base,compiler,tools,standard,work,state,mode,case):
    env=compiler.environment(base)
    env.update(RUSTC_WRAPPER=str(Path(__file__).with_name('profile_wrapper.py')),RUSTC_WORKSPACE_WRAPPER='',
        RUST_INTERP_COMPILER_RUSTC=str(compiler.rustc),RUST_INTERP_STABLE_CGU_PARTITIONING='off',
        RUST_INTERP_EXPORT_PACKAGE=case['package'],RUST_INTERP_EXPORT_TEST='1',
        RUST_INTERP_ENTRIES=json.dumps(case['tests'],separators=(',',':')),
        RUST_INTERP_OUTPUT=str(work/'targets'/mode/'program.rbc'),RUST_INTERP_INLINE_LEAVES='1',
        RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1',RUST_INTERP_RUN_TRY_CALLBACKS='1',
        RUST_INTERP_EXPORT_TIMINGS='1',RUST_INTERP_STD_SYSROOT=str(standard[0]),RUST_INTERP_STD_TARGET=standard[1],
        CARGO_TARGET_DIR=str(work/'targets'/mode),CARGO_ENCODED_RUSTFLAGS='\x1f'.join(flags(mode)),
        STRICT_WARM_PROFILE_REAL_WRAPPER=str(tools/'rust-interp-rustc-wrapper'),
        STRICT_WARM_PROFILE_UNITS=str(work/state/mode/'units'),STRICT_WARM_PROFILE_MODE='self' if state=='edited' else 'off')
    return env

class Admission(RuntimeAdmission):
    def guard(self):
        super().guard()
        for name,item in self.plan['providers'].items():
            require(provider(name)==item,'profile provider changed: '+name)
        for name,item in self.plan['provider_directories'].items():
            path=Path(name)
            require(str(path.resolve(strict=True))==item['resolved'] and (os.readlink(path) if path.is_symlink() else None)==item['link_text'],'profile provider directory changed')

def main():
    a=Admission(NAME,'runtime-ruff-hir-self-profile-v1')
    case=WORKFLOWS['ruff'];file=source_file(SOURCE,case);inventory=read(a.plan['source_inventory']['path'])
    original=file.read_bytes();expected=inventory[str(file.relative_to(SOURCE))]['sha256']
    require(hashlib.sha256(original).hexdigest()==expected,'original Ruff bytes differ')
    text=original.decode();marker='\n#[cfg(test)]\nmod tests {';require(text.count(marker)==1,'original test module')
    label,old,new=case['edits'][0];require(old!=new and text.count(old)==1,'one real edit required')
    candidate=text.replace(old,new);require(candidate.split(marker)[1]==text.split(marker)[1],'test assertions changed');edited=candidate.encode()
    result=dict(status='running',diagnostic_only=True,performance_target_met=False,source=str(SOURCE),original_sha256=expected,edited_sha256=hashlib.sha256(edited).hexdigest(),edit=label,records=[],runtime_key=a.compiler.key,tool_key=a.key,std_key=a.standard[2])
    def save():a.owned.write(a.work/'result.json',result)
    def source_check():return source_inventory(SOURCE,inventory,lambda:a.owned.disk(OWNER,9))
    try:
        with a.admitted():
            require(a.plan['state_order']==[list(x) for x in ORDER] and a.plan['source_inventory']['sha256']==digest(Path(a.plan['source_inventory']['path'])),'profile plan sequence/inventory')
            source_check();(a.work/'tmp').mkdir();(a.work/'targets').mkdir()
            for mode in ['baseline','candidate']:(a.work/'targets'/mode).mkdir()
            for state,mode in ORDER:(a.work/state/mode/'units').mkdir(parents=True)
            save()
            try:
                with SourceEdit(file,original) as edit:
                    for state,mode in ORDER:
                        contents=edited if state=='edited' else original
                        if contents!=edit.current:edit.replace(contents)
                        require(edit.matches(contents),'profile source state differs')
                        out=a.work/state/mode;target=a.work/'targets'/mode
                        env=environment(a.environment,a.compiler,a.tools,a.standard,a.work,state,mode,case)
                        cargo=a.invoke(state+'-'+mode+'-cargo',cargo_command(a.plan['cargo'],a.compiler.host),cwd=SOURCE,environment=env)
                        require(not re.search(r'(?mi)stripping debug info with .?rust-objcopy.? failed|failed to execute rust-objcopy|Library not loaded:|dyld\[',cargo['stdout']+'\n'+cargo['stderr']),'profile strip/loader failure')
                        artifact,event=selected_artifact(cargo['stdout'],target,case['package']);catalog=selected_entry_catalog(artifact,case['tests'])
                        payload=artifact.read_bytes();calls=read(Path(str(artifact)+'.calls.json'));artifact_hash=hashlib.sha256(payload).hexdigest()
                        require(calls['kind']=='unavailable-calls' and calls['schema_version']==1 and calls['strict_frontend'] is True and calls['trap_unsupported_calls'] is True and calls['run_try_callbacks'] is True and calls['artifact_sha256']==artifact_hash,'call report differs')
                        require(isinstance(calls['unavailable_calls'],list) and all(isinstance(site,dict) and all(isinstance(site.get(k),str) for k in ['kind','name','caller','trap_message']) for site in calls['unavailable_calls']),'call sites differ')
                        for suffix in ['', '.entries.json','.calls.json']:
                            data=Path(str(artifact)+suffix).read_bytes();require(len(data)<=64*2**20,'snapshot bound')
                            with (out/('program.rbc'+suffix)).open('xb') as stream:stream.write(data)
                        compilers=compiler_records(out/'units');selected=[r for r in compilers if r['selected']]
                        require(len(selected)==1 and all(c['returncode']==0 for c in compilers),'selected compiler count/status')
                        selected=selected[0];require(selected['parent_pid']==cargo['pid'],'selected compiler parent differs')
                        validate_hir_flags(selected['original_args'],'on' if mode=='candidate' else 'off')
                        require(selected['original_args'].count('-Zincremental-info=true')==1,'actual incremental-info flag')
                        capture=Path(selected['record_path']).parent/'exporter-args.json';actual=read(capture)
                        require(actual['cwd']==str(SOURCE),'actual exporter cwd')
                        validate_hir_flags(actual['args'],'on' if mode=='candidate' else 'off')
                        require(actual['args'].count('-Zincremental-info=true')==1,'actual exporter incremental-info flag')
                        expected_profile_flags=['-Zself-profile='+str(Path(selected['record_path']).parent/'self-profile'),'-Zself-profile-events=default'] if state=='edited' else []
                        require(selected['diagnostic_flags']==expected_profile_flags and [arg for arg in actual['args'] if arg.startswith('-Zself-profile')]==expected_profile_flags,'final profiler arguments differ')
                        require('--sysroot' in actual['args'] and actual['args'][actual['args'].index('--sysroot')+1]==str(a.standard[0]),'actual prepared sysroot')
                        if state=='edited':
                            require(len(compilers)==1 and selected['profiling']=='self' and len(selected['self_profiles'])==1 and not selected['phases'],'edited compile/profile count')
                            raw_profile=Path(selected['self_profiles'][0]['path']);require(raw_profile.suffix=='.mm_profdata','self-profile format')
                            with (out/'selected.mm_profdata').open('xb') as stream:stream.write(raw_profile.read_bytes())
                        else:require(all(c['profiling']=='off' and not c['self_profiles'] for c in compilers),'unrequested compiler profiling')
                        actual_stderr=(Path(selected['record_path']).parent/'stderr.log').read_text()
                        hir=Counter('hit' if line.startswith('[hir-body-reuse]') else 'capture' for line in actual_stderr.splitlines() if line.startswith(('[hir-body-capture]','[hir-body-reuse]')))
                        matches=re.findall(r'Timing report saved to (.+?\.html)',cargo['stderr']);require(len(matches)==1,'Cargo timing report')
                        timing=Path(matches[0].strip('`')).resolve(strict=True);require(timing.is_relative_to(target/'cargo-timings'),'timing route')
                        timing_bytes=timing.read_bytes();require(len(timing_bytes)<=32*2**20,'Cargo timing bound')
                        with (out/'cargo-timing.html').open('xb') as stream:stream.write(timing_bytes)
                        units=units_from_html(timing_bytes)
                        vm=a.invoke(state+'-'+mode+'-vm',vm_command(a.tools,out),cwd=SOURCE)
                        suite,suite_hash=read_report(out/'suite.json');validate_report(suite,case['tests'],'prepared',True);validate_runtime_limits(suite,1000000000,150000,required=True)
                        result['records'].append(dict(state=state,mode=mode,source_sha256=digest(file),artifact_sha256=artifact_hash,artifact_bytes=len(payload),suite_sha256=suite_hash,cargo=cargo['receipt'],vm=vm['receipt'],selected_cargo_event=event,compiler_invocations=compilers,actual_selected_hir_events=dict(hir),selected_exporter_stages=exporter_seconds(actual_stderr),cargo_units=units,cargo_timeline=timeline(units),instrumented=state=='edited'))
                        save()
            finally:
                result['restored_source']=source_check();save()
            for mode in ['baseline','candidate']:
                out=a.work/'edited'/mode;profile=out/'selected.mm_profdata';before=digest(profile)
                a.invoke('summarize-'+mode,[a.plan['summarizer'],'summarize',str(profile),'--json'],cwd=out)
                require(digest(profile)==before,'reader changed profile');summary=out/'selected.json';require(summary.is_file() and not summary.is_symlink() and summary.stat().st_size<=32*2**20,'profile summary missing/oversized')
                result.setdefault('query_summaries',{})[mode]=dict(path=str(summary),sha256=digest(summary),profile_sha256=before)
            for state in ['prime','edited','restored']:
                pair=[row['artifact_sha256'] for row in result['records'] if row['state']==state]
                require(len(pair)==2 and pair[0]==pair[1],'off/on selected bytecode differs')
            result.update(cross_mode_bytecode_equal=True,status='passed',commands=len(a.record['children']),assertions_unchanged=True,scope='Selected-process self-profile diagnosis, fresh metadata-only targets, no native application baseline build or strict latency claim.')
            save();a.finish(result)
    except BaseException as error:
        result.update(status='failed',error=repr(error));save();a.failed(error);raise
if __name__=='__main__':main()

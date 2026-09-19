#!/usr/bin/env python3
"""Finish the saved off/on profile history without repeating a completed compile."""
from collections import Counter
import hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_admission_v2 import RuntimeAdmission,OWNER,R_OWNER,read,validate_hir_flags
from run_ruff_diagnostic import provider,observed_hir
from profile_helpers import require,digest,selected_artifact,compiler_records,source_inventory
from workflow_cases import WORKFLOWS
from workflow_case_file import source_file
from workflow_io import SourceEdit
from interpreter import selected_entry_catalog
from suite_reports import read_report,validate_report,validate_runtime_limits
from cargo_timing_data import units_from_html,timeline
from workflow_controls import exporter_seconds
NAME='ruff-hir-self-profile-continuation-01'
PRIOR=OWNER/'.work/ruff-hir-self-profile-02'
SOURCE=R_OWNER/'.work/sources/ruff'
WRAPPER=OWNER/'experiments/runtime-application-admission/ruff-profile-02/profile_wrapper.py'
ORDER=[('edited','baseline'),('restored','baseline'),('restored','candidate')]

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
    env.update(RUSTC_WRAPPER=str(WRAPPER),RUSTC_WORKSPACE_WRAPPER='',RUST_INTERP_COMPILER_RUSTC=str(compiler.rustc),RUST_INTERP_STABLE_CGU_PARTITIONING='off',RUST_INTERP_EXPORT_PACKAGE=case['package'],RUST_INTERP_EXPORT_TEST='1',RUST_INTERP_ENTRIES=json.dumps(case['tests'],separators=(',',':')),RUST_INTERP_OUTPUT=str(PRIOR/'targets'/mode/'program.rbc'),RUST_INTERP_INLINE_LEAVES='1',RUST_INTERP_TRAP_UNSUPPORTED_CALLS='1',RUST_INTERP_RUN_TRY_CALLBACKS='1',RUST_INTERP_EXPORT_TIMINGS='1',RUST_INTERP_STD_SYSROOT=str(standard[0]),RUST_INTERP_STD_TARGET=standard[1],CARGO_TARGET_DIR=str(PRIOR/'targets'/mode),CARGO_ENCODED_RUSTFLAGS='\x1f'.join(flags(mode)),STRICT_WARM_PROFILE_REAL_WRAPPER=str(tools/'rust-interp-rustc-wrapper'),STRICT_WARM_PROFILE_UNITS=str(work/state/mode/'units'),STRICT_WARM_PROFILE_MODE='self' if state=='edited' else 'off')
    return env

def stamp(path):
    s=path.lstat();return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]

class Admission(RuntimeAdmission):
    def guard(self):
        super().guard()
        for name,item in self.plan['providers'].items():require(provider(name)==item,'provider changed: '+name)
        for name,item in self.plan['provider_directories'].items():
            path=Path(name);require(str(path.resolve(strict=True))==item['resolved'] and (os.readlink(path) if path.is_symlink() else None)==item['link_text'],'provider directory changed')
        for name,item in self.plan['prior_evidence'].items():
            path=Path(name);before=stamp(path)
            require(path.resolve(strict=True)==path and path.is_file() and before==item['stamp'] and digest(path)==item['sha256'] and stamp(path)==before,'prior evidence changed: '+name)
        found=sorted(str(p) for p in PRIOR.rglob('*') if not p.is_relative_to(PRIOR/'targets') and (p.is_symlink() or not p.is_dir()))
        require(found==sorted(self.plan['prior_evidence']),'failed evidence membership changed')
    def budget(self):
        free=self.owned.disk(OWNER,9);allocated=0
        for root in [PRIOR,self.work]:
            require(root.resolve(strict=True)==root,'indirect owned profile root')
            for directory,dirs,files in os.walk(root,followlinks=False):
                for name in dirs+files:allocated+=(Path(directory)/name).lstat().st_blocks*512
        require(allocated<=self.plan['allocated_byte_limit'],'combined original/continuation allocation bound')
        return dict(free_bytes=free,allocated_bytes=allocated)

def validate_compile(a,case,state,mode,cargo,out,units_root):
    target=PRIOR/'targets'/mode
    require(cargo['returncode']==0 and cargo['command']==cargo_command(a.plan['cargo'],a.compiler.host),'Cargo status/argv')
    require(not re.search(r'(?mi)stripping debug info with .?rust-objcopy.? failed|failed to execute rust-objcopy|Library not loaded:|dyld\[',cargo['stdout']+'\n'+cargo['stderr']),'strip/loader failure')
    artifact,event=selected_artifact(cargo['stdout'],target,case['package']);selected_entry_catalog(artifact,case['tests'])
    payload=artifact.read_bytes();artifact_hash=hashlib.sha256(payload).hexdigest();calls=read(Path(str(artifact)+'.calls.json'))
    require(calls['kind']=='unavailable-calls' and calls['schema_version']==1 and calls['strict_frontend'] is True and calls['trap_unsupported_calls'] is True and calls['run_try_callbacks'] is True and calls['artifact_sha256']==artifact_hash,'call report')
    require(isinstance(calls['unavailable_calls'],list) and all(isinstance(site,dict) and all(isinstance(site.get(k),str) for k in ['kind','name','caller','trap_message']) for site in calls['unavailable_calls']),'call sites')
    for suffix in ['', '.entries.json','.calls.json']:
        data=Path(str(artifact)+suffix).read_bytes();require(len(data)<=64*2**20,'snapshot bound')
        with (out/('program.rbc'+suffix)).open('xb') as stream:stream.write(data)
    compilers=compiler_records(units_root);selected=[r for r in compilers if r['selected']];compiled=[r for r in compilers if r['compilation']]
    require(len(selected)==len(compiled)==1 and selected==compiled and all(r['returncode']==0 for r in compilers),'one actual selected compilation required')
    require(all(r['selected'] or (not r['compilation'] and r['profiling']=='off' and not r['self_profiles']) for r in compilers),'unselected compilation/profile')
    selected=selected[0];require(selected['parent_pid']==cargo['pid'] and selected['original_args'][0]==str(a.compiler.rustc),'actual compiler parent/route')
    validate_hir_flags(selected['original_args'],'on' if mode=='candidate' else 'off')
    capture=Path(selected['record_path']).parent/'exporter-args.json';actual=read(capture)
    require(actual['cwd']==str(SOURCE),'exporter cwd');validate_hir_flags(actual['args'],'on' if mode=='candidate' else 'off')
    for argv in [selected['original_args'],actual['args']]:require(argv.count('-Zincremental-info=true')==1,'incremental-info flag')
    expected_profile_flags=['-Zself-profile='+str(Path(selected['record_path']).parent/'self-profile'),'-Zself-profile-events=default'] if state=='edited' else []
    require(selected['diagnostic_flags']==expected_profile_flags and [v for v in actual['args'] if v.startswith('-Zself-profile')]==expected_profile_flags,'profiler arguments')
    require('--sysroot' in actual['args'] and actual['args'][actual['args'].index('--sysroot')+1]==str(a.standard[0]),'prepared sysroot')
    require(selected['forwarded_command']==[str(a.tools/'rust-interp-rustc-wrapper'),selected['original_args'][0],*expected_profile_flags,*selected['original_args'][1:]],'wrapper forwarding changed')
    if state=='edited':
        require(selected['profiling']=='self' and len(selected['self_profiles'])==1 and not selected['phases'],'one selected profile')
        profile=Path(selected['self_profiles'][0]['path']);require(profile.name==f"ruff_linter-{selected['child_pid']:07}.mm_profdata",'profile child identity')
        with (out/'selected.mm_profdata').open('xb') as stream:
            with profile.open('rb') as source:
                while block:=source.read(2**20):a.owned.disk(OWNER,9);stream.write(block)
        require(digest(out/'selected.mm_profdata')==digest(profile),'profile snapshot differs')
    else:require(all(r['profiling']=='off' and not r['self_profiles'] for r in compilers),'unrequested profile')
    stderr=(Path(selected['record_path']).parent/'stderr.log').read_text()
    hir=observed_hir([dict(mode=mode,cycle=0,state=1 if state=='edited' else -2,phase=state,calls=[dict(stderr=stderr)])])
    matches=re.findall(r'Timing report saved to (.+?\.html)',cargo['stderr']);require(len(matches)==1,'Cargo timing report')
    timing=Path(matches[0].strip('`')).resolve(strict=True);require(timing.is_relative_to(target/'cargo-timings'),'timing route')
    timing_bytes=timing.read_bytes();require(len(timing_bytes)<=32*2**20,'Cargo timing bound')
    with (out/'cargo-timing.html').open('xb') as stream:stream.write(timing_bytes)
    units=units_from_html(timing_bytes)
    return dict(state=state,mode=mode,artifact_sha256=artifact_hash,artifact_bytes=len(payload),compiler_invocations=compilers,informational_probes=len(compilers)-1,selected_cargo_event=event,selected_hir=hir,selected_exporter_stages=exporter_seconds(stderr),cargo_units=units,cargo_timeline=timeline(units),instrumented=state=='edited',cargo=cargo['receipt'])

def main():
    a=Admission(NAME,'runtime-ruff-hir-self-profile-continuation-v1');case=WORKFLOWS['ruff'];file=source_file(SOURCE,case);inventory=read(a.plan['source_inventory']['path']);previous=read(PRIOR/'result.json')
    require(previous['status']=='failed' and previous['error']=="RuntimeError('self-profile output exceeds bound')" and previous['restored_source']==dict(files=11119,bytes=89102713,exact_membership=True),'failed history differs')
    original=file.read_bytes();require(hashlib.sha256(original).hexdigest()==previous['original_sha256'],'source not restored')
    text=original.decode();marker='\n#[cfg(test)]\nmod tests {';label,old,new=case['edits'][0];require(text.count(old)==1 and text.count(marker)==1,'edit/test marker')
    edited=text.replace(old,new).encode();require(edited.decode().split(marker)[1]==text.split(marker)[1] and hashlib.sha256(edited).hexdigest()==previous['edited_sha256'],'edit/assertions differ')
    result=dict(status='running',diagnostic_only=True,performance_target_met=False,previous_receipt=a.plan['prior_receipt'],completed_compiles_rerun=False,records=[])
    def save():a.owned.write(a.work/'result.json',result)
    def source_check():return source_inventory(SOURCE,inventory,lambda:a.owned.disk(OWNER,9))
    def execute_vm(state,mode,out,row):
        vm=a.invoke(state+'-'+mode+'-vm',vm_command(a.tools,out),cwd=SOURCE)
        suite,suite_hash=read_report(out/'suite.json');validate_report(suite,case['tests'],'prepared',True);validate_runtime_limits(suite,1000000000,150000,required=True)
        row.update(vm=vm['receipt'],suite_sha256=suite_hash);result['records'].append(row);save()
    try:
        with a.admitted():
            source_check();(a.work/'tmp').mkdir()
            for state,mode in [('edited','candidate'),*ORDER]:(a.work/state/mode/'units').mkdir(parents=True)
            save()
            # Every original successful prime and raw child remains bound; no
            # source edit, compiler, or test from those primes is repeated.
            for oldrow in previous['records']:
                require(oldrow['state']=='prime','unexpected completed state')
                out=PRIOR/'prime'/oldrow['mode'];suite,_=read_report(out/'suite.json',oldrow['suite_sha256']);validate_report(suite,case['tests'],'prepared',True)
                require(digest(out/'program.rbc')==oldrow['artifact_sha256'],'prime artifact changed')
            saved=a.plan['completed_candidate_cargo'];receipt=read(saved);folder=Path(saved).parent
            cargo=dict(receipt,receipt=saved,stdout=(folder/'stdout').read_text(),stderr=(folder/'stderr').read_text())
            out=a.work/'edited/candidate';row=validate_compile(a,case,'edited','candidate',cargo,out,PRIOR/'edited/candidate/units')
            for suffix in ['', '.entries.json','.calls.json']:require((out/('program.rbc'+suffix)).read_bytes()==(PRIOR/'edited/candidate'/('program.rbc'+suffix)).read_bytes(),'saved selected snapshot differs')
            row.update(source_sha256=previous['edited_sha256'],saved_actual_compile=True);execute_vm('edited','candidate',out,row)
            try:
                with SourceEdit(file,original) as edit:
                    for state,mode in ORDER:
                        contents=edited if state=='edited' else original
                        if edit.current!=contents:edit.replace(contents)
                        require(edit.matches(contents),'source state changed')
                        env=environment(a.environment,a.compiler,a.tools,a.standard,a.work,state,mode,case)
                        cargo=a.invoke(state+'-'+mode+'-cargo',cargo_command(a.plan['cargo'],a.compiler.host),cwd=SOURCE,environment=env)
                        out=a.work/state/mode;row=validate_compile(a,case,state,mode,cargo,out,out/'units');row.update(source_sha256=digest(file),saved_actual_compile=False);execute_vm(state,mode,out,row)
            finally:result['restored_source']=source_check();save()
            profile_sizes=[(a.work/'edited'/mode/'selected.mm_profdata').stat().st_size for mode in ['baseline','candidate']]
            require(all(n<=256*2**20 for n in profile_sizes) and sum(profile_sizes)<=512*2**20,'combined profile bound')
            for mode in ['baseline','candidate']:
                out=a.work/'edited'/mode;profile=out/'selected.mm_profdata';before=digest(profile)
                a.invoke('summarize-'+mode,[a.plan['summarizer'],'summarize',str(profile),'--json'],cwd=out)
                require(digest(profile)==before,'reader changed profile');summary=out/'selected.json';require(summary.resolve(strict=True)==summary and summary.is_file() and summary.stat().st_size<=32*2**20,'summary bound')
                result.setdefault('query_summaries',{})[mode]=dict(path=str(summary),sha256=digest(summary),profile_sha256=before)
            for state in ['edited','restored']:
                pair=[row['artifact_sha256'] for row in result['records'] if row['state']==state];require(len(pair)==2 and pair[0]==pair[1],'off/on bytecode differs')
            result.update(status='passed',commands=len(a.record['children']),assertions_unchanged=True,cross_mode_bytecode_equal=True,scope='Saved candidate plus remaining originally planned profile history; diagnostic only.')
            save();a.finish(result)
    except BaseException as error:result.update(status='failed',error=repr(error));save();a.failed(error);raise
if __name__=='__main__':main()

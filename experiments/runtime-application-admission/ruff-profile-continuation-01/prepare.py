#!/usr/bin/env python3
"""Freeze only the unfinished portion of the failed profile history."""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('ruff_profile_continuation',HERE/'continue.py');a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
from runtime_compiler import load_runtime_compiler
from runtime_tools import validate_tool_runtime
from interpreter import installed_tools
from std_mir_source_paths import load as load_std,namespace_for
from run_ruff_diagnostic import provider

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,value):
    with p.open('x') as f:f.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
def main():
    a.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==a.OWNER,'fixed owner/Python')
    olddir=HERE.with_name('ruff-profile-02')/'plan';old=a.read(olddir/'plan.json');oldfreeze=a.read(olddir/'inputs.json')
    compiler=load_runtime_compiler(a.R_OWNER,old['runtime_key']);tools,key=installed_tools(old['tool_key']);validate_tool_runtime(tools,key,compiler)
    work=a.OWNER/'.work'/a.NAME;env=dict(old['child_environment'],TMPDIR=str(work/'tmp')+'/');saved=dict(os.environ);os.environ.clear();os.environ.update(env)
    try:standard=load_std(a.R_OWNER,old['std_key'],compiler,namespace_for('source-paths-v2-shared','unused-shared-policy'))
    finally:os.environ.clear();os.environ.update(saved)
    a.require(a.read(tools/'compiler.json')==old['runtime_composition'],'runtime tools changed')
    terminal=a.read(a.PRIOR/'supervision.json');result=a.read(a.PRIOR/'result.json')
    a.require(terminal['status']=='failed' and result['status']=='failed' and result['error']=="RuntimeError('self-profile output exceeds bound')" and len(terminal['children'])==5,'failed predecessor differs')
    a.require([(r['state'],r['mode']) for r in result['records']]==[('prime','baseline'),('prime','candidate')] and result['restored_source']==dict(files=11119,bytes=89102713,exact_membership=True),'completed predecessor states/restoration')
    completed=terminal['children'][-1];completed_path=Path(completed['path'])/'receipt.json'
    a.require(completed['label']=='edited-candidate-cargo' and completed['receipt']==a.read(completed_path) and completed['receipt']['returncode']==0,'completed candidate compile')
    prior_files=sorted(p for p in a.PRIOR.rglob('*') if not p.is_relative_to(a.PRIOR/'targets') and (p.is_symlink() or not p.is_dir()))
    prior_evidence={}
    for p in prior_files:
        a.require(p.resolve(strict=True)==p and p.is_file(),'ordinary prior evidence required');before=a.stamp(p)
        prior_evidence[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size,stamp=before);a.require(a.stamp(p)==before,'prior evidence changed while freezing')
    profiles=list((a.PRIOR/'edited/candidate/units').rglob('*.mm_profdata'));a.require(len(profiles)==1 and profiles[0].stat().st_size==172033161 and sha(profiles[0])=='76b73889ddc3cbd3c7855364f2325450ad0ab9afde701ba06c3c2b03644ebe72','saved actual candidate profile')
    case=a.WORKFLOWS['ruff'];commands=[dict(label='edited-candidate-vm',command=a.vm_command(tools,work/'edited/candidate'),cwd=str(a.SOURCE),expected_returncode=0)]
    for state,mode in a.ORDER:
        out=work/state/mode
        commands.append(dict(label=state+'-'+mode+'-cargo',command=a.cargo_command(old['cargo'],compiler.host),cwd=str(a.SOURCE),expected_returncode=0,environment=a.environment(env,compiler,tools,standard,work,state,mode,case)))
        commands.append(dict(label=state+'-'+mode+'-vm',command=a.vm_command(tools,out),cwd=str(a.SOURCE),expected_returncode=0))
    for mode in ['baseline','candidate']:
        out=work/'edited'/mode;commands.append(dict(label='summarize-'+mode,command=[old['summarizer'],'summarize',str(out/'selected.mm_profdata'),'--json'],cwd=str(out),expected_returncode=0))
    producer_paths=[*sorted((a.R_OWNER/'scripts').glob('*.py')),HERE/'continue.py',HERE/'profile_helpers.py',HERE/'prepare.py',HERE.parent/'runtime_admission_v2.py',HERE.parent/'run_ruff_diagnostic.py',a.WRAPPER,a.OWNER/'experiments/stable-cgu/owned_stage.py',a.OWNER/'scripts/supervise_experiment.py']
    plan={k:v for k,v in old.items() if k not in ['status','name','policy','state_order','commands','launch_environment','child_environment','producer_sources','prior_diagnostic']}
    plan.update(status='unexecuted',name=a.NAME,policy='runtime-ruff-hir-self-profile-continuation-v1',commands=commands,child_environment=env,launch_environment=env,producer_sources={str(p):sha(p) for p in producer_paths},prior_receipt=ref(a.PRIOR/'supervision.json'),prior_result=ref(a.PRIOR/'result.json'),prior_evidence=prior_evidence,completed_candidate_cargo=str(completed_path),completed_candidate_profile=ref(profiles[0]),remaining_order=[list(x) for x in a.ORDER],completed_compiles_rerun=False,allocated_byte_limit=6*2**30)
    plan['bounds']=dict(plan['bounds'],profile_file_bytes=256*2**20,profile_total_bytes=512*2**20)
    destination=HERE/'plan';a.require(not destination.exists(),'fresh continuation plan required');destination.mkdir();write(destination/'plan.json',plan)
    files=set(map(Path,oldfreeze['files']))|set(producer_paths)|set(olddir.iterdir())|{destination/'plan.json',a.PRIOR/'supervision.json',a.PRIOR/'result.json'}
    for directory in [a.OWNER/'.work/experiments/ruff-hir-self-profile-supervisor-02',a.OWNER/'.work/ruff-hir-profile-launch-execution-02']:files.update(p for p in directory.rglob('*') if p.is_file())
    files.add(a.OWNER/'.work/launch_ruff_profile_02.py')
    a.require(all(p.resolve(strict=True)==p and p.is_file() and p.stat().st_size<=32*2**20 for p in files),'ordinary bounded inputs')
    total=sum(p.stat().st_size for p in files);a.require(total<=96*2**20,'retained source bound')
    python=Path('/opt/homebrew/bin/python3');frozen=dict(schema_version=1,owner=str(a.OWNER),python=dict(resolved=str(python.resolve()),sha256=sha(python)),files={str(p):sha(p) for p in sorted(files)})
    write(destination/'inputs.json',frozen)
    probe=a.Admission.__new__(a.Admission);probe.plan_path=destination/'plan.json';probe.freeze_path=destination/'inputs.json';probe.freeze_sha=sha(probe.freeze_path);probe.plan=plan;probe.freeze=frozen;probe.source_files=plan['producer_sources'];probe.compiler=compiler;probe.tools=tools;probe.key=key;probe.standard=standard
    began=time.time();saved=dict(os.environ);os.environ.clear();os.environ.update(env)
    try:probe.guard()
    finally:os.environ.clear();os.environ.update(saved)
    write(destination/'metadata-preflight.json',dict(status='passed',source_freeze_sha256=sha(destination/'inputs.json'),pid=os.getpid(),started_at=began,finished_at=time.time(),guard='actual source/runtime/tools/std/config/provider/prior-evidence read-only checks',workload_children=0,work_directory_created=False))
    launch=dict(owner=str(a.OWNER),cwd=str(a.OWNER),environment=env,helper=ref(HERE/'continue.py'),plan=ref(destination/'plan.json'),source_freeze=ref(destination/'inputs.json'),command=[str(python),'-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id','ruff-hir-self-profile-continuation-supervisor-01','--',str(python),'-B',str(HERE/'continue.py'),'--plan',str(destination/'plan.json'),'--freeze',str(destination/'inputs.json'),'--freeze-sha256',sha(destination/'inputs.json')],canonical_lock=plan['canonical_lock'],wait_seconds=600,expected_children=9,review_required_before_launch=True)
    write(destination/'launch.json',launch);print(json.dumps(dict(launch=ref(destination/'launch.json'),freeze=ref(destination/'inputs.json'),plan=ref(destination/'plan.json'),files=len(files),bytes=total,prior_files=len(prior_evidence),prior_bytes=sum(x['bytes'] for x in prior_evidence.values())),indent=2))
if __name__=='__main__':main()

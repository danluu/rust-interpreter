#!/usr/bin/env python3
"""Freeze the selected-process profile plan; no compiler or application execution."""
import hashlib,json,os,stat,struct,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import profile as a
from runtime_admission import read,OWNER,R_OWNER
from runtime_compiler import load_runtime_compiler
from runtime_tools import validate_tool_runtime
from interpreter import installed_tools
from std_mir_source_paths import load as load_std,namespace_for
from run_ruff_diagnostic import provider
RUNTIME_KEY='eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03'
STD_KEY='e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63'
TOOL_KEY='7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a'
READER_OWNER=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
READER=READER_OWNER/'.work/measureme-target/release/summarize'
READER_SOURCE=READER_OWNER/'.work/sources/measureme-12.0.3'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
def write(p,value):
    with p.open('x') as f:f.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
def main():
    a.require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd()==OWNER,'fixed owner/Python -B')
    old=read(HERE.parent/'ruff-diagnostic-01/plan.json');oldfreeze=read(HERE.parent/'ruff-diagnostic-01/inputs.json')
    compiler=load_runtime_compiler(R_OWNER,RUNTIME_KEY);tools,key=installed_tools(TOOL_KEY);validate_tool_runtime(tools,key,compiler)
    for option in ['self-profile','self-profile-events']:compiler.require_option(option)
    work=OWNER/'.work'/a.NAME;env=dict(old['environment'],TMPDIR=str(work/'tmp')+'/')
    # The std policy binds the same absolute Cargo configuration paths. Install
    # only the reviewed environment for the ordinary ready-reader call here.
    saved=dict(os.environ);os.environ.clear();os.environ.update(env)
    try:standard=load_std(R_OWNER,STD_KEY,compiler,namespace_for('source-paths-v2-shared','unused-shared-policy'))
    finally:os.environ.clear();os.environ.update(saved)
    a.require(read(tools/'compiler.json')==old['runtime_composition'],'installed composition changed')
    for reference in [old['tool_publication'],old['published_tools']]:a.require(sha(reference['path'])==reference['sha256'],'publication proof changed')
    a.require(sha(READER)=='748510b478136ead21d185fccb317eb8ea5128f7d78343b395d1e4b645fce9d8','qualified reader changed')
    receipt=READER_OWNER/'.work/strict-warm-build/measureme-build-01/summary.json'
    a.require(sha(receipt)=='3f59bec0d3f30c6450aeae05b5179a2a594f24ad71ba464f622f930ba6a7471f','reader build receipt changed')
    reader_build=read(receipt)
    a.require(reader_build['status']=='passed' and reader_build['sha256']==sha(READER) and reader_build['binary']==str(READER) and reader_build['source_commit']=='5ac839c602b59eee9c908b3b35b6d6c0cd1c42f7' and reader_build['lock_sha256']==sha(READER_SOURCE/'Cargo.lock'),'reader source/build association')
    b=READER.read_bytes();magic,cpu,sub,kind,count,size,flags,reserved=struct.unpack_from('<8I',b)
    a.require(magic==0xfeedfacf and cpu==0x100000c and kind==2,'reader thin ARM64 executable required')
    offset=32;libraries=[];rpaths=[]
    for index in range(count):
        command,length=struct.unpack_from('<II',b,offset);a.require(length>=8 and offset+length<=32+size,'reader load command bounds')
        if command in [0xc,0x80000018,0x8000001f,0x20,0x80000023,0x8000001c]:
            start=struct.unpack_from('<I',b,offset+8)[0];a.require(0<start<length,'reader load string bounds');text=b[offset+start:offset+length].split(b'\0',1)[0].decode()
            (rpaths if command==0x8000001c else libraries).append(text)
        offset+=length
    a.require(offset==32+size and libraries==['/usr/lib/libiconv.2.dylib','/usr/lib/libSystem.B.dylib'] and not rpaths,'reader non-system loader dependency')
    configuration=old['configuration'];executor_paths=[*map(Path,old['executors']),READER]
    cargo=Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin/bin/cargo')
    case=a.WORKFLOWS['ruff'];commands=[]
    for state,mode in a.ORDER:
        out=work/state/mode
        commands.append(dict(label=state+'-'+mode+'-cargo',command=a.cargo_command(cargo,compiler.host),cwd=str(a.SOURCE),expected_returncode=0,environment=a.environment(env,compiler,tools,standard,work,state,mode,case)))
        commands.append(dict(label=state+'-'+mode+'-vm',command=a.vm_command(tools,out),cwd=str(a.SOURCE),expected_returncode=0))
    for mode in ['baseline','candidate']:
        out=work/'edited'/mode
        commands.append(dict(label='summarize-'+mode,command=[str(READER),'summarize',str(out/'selected.mm_profdata'),'--json'],cwd=str(out),expected_returncode=0))
    producer_paths=[*sorted((R_OWNER/'scripts').glob('*.py')),HERE/'profile.py',HERE/'profile_wrapper.py',HERE/'profile_helpers.py',HERE/'prepare.py',HERE.parent/'runtime_admission.py',HERE.parent/'run_ruff_diagnostic.py',OWNER/'experiments/stable-cgu/owned_stage.py',OWNER/'scripts/supervise_experiment.py']
    plan=dict(schema_version=1,status='unexecuted',name=a.NAME,policy='runtime-ruff-hir-self-profile-v1',owner=str(OWNER),runtime_owner=str(R_OWNER),runtime_key=RUNTIME_KEY,std_key=STD_KEY,tool_key=key,runtime_composition=old['runtime_composition'],tool_publication=old['tool_publication'],published_tools=old['published_tools'],state_order=[list(x) for x in a.ORDER],source_inventory=old['source_inventory'],source_acquisition=old['source_acquisition'],prior_diagnostic=ref(OWNER/'.work/ruff-hir-diagnostic-supervision-01/receipt.json'),corrected_prior_attribution=ref(OWNER/'.work/ruff-hir-diagnostic-attribution-correction-01.json'),child_environment=env,launch_environment=env,platform=list(os.uname()),configuration=configuration,executor_routes={str(p):provider(p) for p in executor_paths},providers=old['providers'],provider_directories=old['provider_directories'],producer_sources={str(p):sha(p) for p in producer_paths},canonical_lock=old['canonical_lock'],wait_seconds=600,commands=commands,cargo=str(cargo),summarizer=str(READER),reader_proof=dict(binary=ref(READER),build_receipt=ref(receipt),source_revision='5ac839c602b59eee9c908b3b35b6d6c0cd1c42f7',source_cargo_lock=ref(READER_SOURCE/'Cargo.lock'),mach_o=dict(libraries=libraries,rpaths=rpaths),system_loader_assumption='Absolute libSystem/libiconv are supplied by this recorded macOS shared cache; system shared-cache bytes are not copied.'),allocated_byte_limit=6*2**30,bounds=dict(entry_free_gib=16,active_child_stop_gib=9,running_floor_gib=8,input_bytes=96*2**20,input_file_bytes=32*2**20,profile_file_bytes=128*2**20,profile_total_bytes=256*2**20),timing_scope='Diagnostic selected-process profile; no latency qualification',performance_qualified=False,strict_application_readiness_qualified=False)
    destination=HERE/'plan';a.require(not destination.exists(),'fresh profile plan required');destination.mkdir();write(destination/'plan.json',plan)
    files=set(map(Path,oldfreeze['files']))|set(producer_paths)|{destination/'plan.json',READER,receipt,READER_SOURCE/'Cargo.lock',READER_SOURCE/'Cargo.toml',OWNER/'.work/ruff-hir-diagnostic-supervision-01/receipt.json',OWNER/'.work/ruff-hir-diagnostic-attribution-correction-01.json'}
    files.update(READER_SOURCE.rglob('*.rs'))
    a.require(all(p.resolve(strict=True)==p and p.is_file() and p.stat().st_size<=32*2**20 for p in files),'ordinary bounded frozen inputs')
    total=sum(p.stat().st_size for p in files);a.require(total<=96*2**20,'profile input bound')
    python=Path('/opt/homebrew/bin/python3');frozen=dict(schema_version=1,owner=str(OWNER),python=dict(resolved=str(python.resolve()),sha256=sha(python)),files={str(p):sha(p) for p in sorted(files)})
    write(destination/'inputs.json',frozen)
    launch=dict(owner=str(OWNER),cwd=str(OWNER),environment=env,helper=ref(HERE/'profile.py'),plan=ref(destination/'plan.json'),source_freeze=ref(destination/'inputs.json'),command=[str(python),'-B',str(OWNER/'scripts/supervise_experiment.py'),'--run-id','ruff-hir-self-profile-supervisor-01','--',str(python),'-B',str(HERE/'profile.py'),'--plan',str(destination/'plan.json'),'--freeze',str(destination/'inputs.json'),'--freeze-sha256',sha(destination/'inputs.json')],canonical_lock=old['canonical_lock'],wait_seconds=600,expected_children=14,review_required_before_launch=True)
    write(destination/'launch.json',launch);print(json.dumps(dict(launch=ref(destination/'launch.json'),freeze=ref(destination/'inputs.json'),plan=ref(destination/'plan.json'),files=len(files),bytes=total),indent=2))
if __name__=='__main__':main()

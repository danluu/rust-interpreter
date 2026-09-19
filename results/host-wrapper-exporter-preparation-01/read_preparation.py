"""Finite saved preparation/source readback; no provider payload walks/imports."""
from pathlib import Path
import hashlib
import json
import os
import re
import stat

Q=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
F=Q/'experiments/host-wrapper-exporter-01'
P=F/'packet-01'
PREFIX=X/'.work/host-wrapper-exporter-source-01'
WORK=X/'.work/host-wrapper-exporter-metadata-01'
TARGET=X/'.work/host-wrapper-exporter-target-01'
KEY='f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
RUNTIME=R/'.work/runtime-compilers'/KEY/'sysroot'
D2=X/'.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin/stage0'
B3=X/'.work/hir-options-hash-compiler-01/beta-sysroot'
refs={}

def stamp(path):
    s=path.lstat()
    return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]

def read(path,digest=None):
    path=Path(path);s=stamp(path)
    assert stat.S_ISREG(s[2]) and s[3]<=16*2**20 and path.resolve(strict=True)==path
    b=path.read_bytes();assert len(b)==s[3] and stamp(path)==s
    row=dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),identity=s)
    assert digest is None or row['sha256']==digest,str(path)
    refs[str(path)]=row
    return b

def doc(path,digest=None):return json.loads(read(path,digest))

def check_ref(row):
    read(row['path'],row['sha256'])
    assert refs[row['path']]==row,row['path']

parent_path=Q/'.work/host-wrapper-exporter-preparation-execution-01/record.json'
parent=doc(parent_path,'1408d4a14931c289f469d6ac8a1d9a669bb3801e110bb7f6977c257c82e641b1')
assert parent['status']=='finished' and parent['returncode']==0 and parent['child_may_be_live'] is False
assert parent['parent_pid']==93279 and parent['child_pid']==94000 and parent['preparation_verified'] is True
assert parent['signals']==parent['retries']==0
read(parent['source']['path'],parent['source']['sha256'])
receipt=doc(parent['receipt']['path'],parent['receipt']['sha256'])
assert receipt['status']=='passed' and receipt['pid']==parent['child_pid'] and receipt['parent_pid']==parent['parent_pid']
assert receipt['command']==parent['command'][2:] and receipt['cwd']==parent['cwd']==str(X)
times=[parent['started_at'],receipt['started_at'],receipt['admitted_at'],receipt['finished_at'],parent['finished_at']]
assert times==sorted(times) and receipt['compiler_calls']==receipt['provider_probes']==receipt['signals']==receipt['retries']==0
assert receipt['entry_free_bytes']>=16*2**30 and receipt['free_bytes_after']>=8*2**30
assert doc(parent_path.parent/'stdout',parent['stdout_sha256'])==receipt
assert read(parent_path.parent/'stderr',parent['stderr_sha256'])==b''
assert {p.name for p in parent_path.parent.iterdir()}=={'record.json','stdout','stderr'}
assert {p.name for p in Path(parent['receipt']['path']).parent.iterdir()}=={'record.json'}
for field in ('plan','inputs','launch','compiler_roles'):check_ref(receipt['outputs'][field])
assert {p.name for p in P.iterdir()}=={'plan.json','inputs.json','launch.json','compiler-roles.json'}
plan=doc(P/'plan.json','922663c1d01f2fcf88e5f7b74658ec6e66fc47fb1f5f4bee949d3901da5c32e8')
launch=doc(P/'launch.json','450085144d49d9b15442dc848cd48b5784da6c3b21d36710b932727e9f41d591')
inputs=doc(P/'inputs.json','de44d4b4bc7685097ba2d0f1e2bcf50fa231a05658092bde87b5d59f17519c8e')
roles=doc(P/'compiler-roles.json','8f91fae6e1acc30eaedb0c2ff34d7b380c5ead20352ca42b807a82b972d8935a')
sources=doc(F/'sources.json',receipt['sources_sha256'])['files']
assert sources==inputs['files'] and len(sources)==17
assert launch['inputs']==receipt['outputs']['inputs'] and launch['plan']==inputs['plan']==receipt['outputs']['plan']
assert launch['command']==['/opt/homebrew/bin/python3','-B',str(F/'metadata.py'),'--inputs-sha256',refs[str(P/'inputs.json')]['sha256'],'--sources-sha256',receipt['sources_sha256']]
assert launch['cwd']==plan['owner']==str(X) and launch['status']=='unexecuted' and plan['status']=='prepared-unexecuted'
assert launch['capacity']==plan['capacity']==dict(entry_gib=16,stop_gib=9,floor_gib=8)
assert plan['canonical_lock']=='/Users/danluu/dev/rust-interp/.work/benchmark.lock' and plan['wait_seconds']==600
assert launch['environment']==plan['launch_environment'] and plan['binding']==roles
assert plan['runtime_key']==KEY and plan['source_root']==str(PREFIX)
assert plan['host_codegen_application_qualified'] is False and plan['application_qualified'] is False and plan['performance_measurement'] is False
assert plan['compiler_builds']==plan['exporter_builds']==0
for path,digest in sources.items():
    read(path,digest);assert refs[path]==plan['files'][path]
for path,row in plan['files'].items():
    assert set(row)=={'path','sha256','bytes','identity'} and row['path']==path and Path(path).is_absolute()
    assert re.fullmatch('[0-9a-f]{64}',row['sha256']) and type(row['bytes']) is int and row['bytes']>=0
    assert len(row['identity'])==7 and all(type(v) is int for v in row['identity'])
    assert stat.S_ISREG(row['identity'][2]) and row['identity'][3]==row['bytes']
assert len(plan['files'])==receipt['outputs']['current_input_files']==5685
census=doc(plan['source_snapshot_census']['path'],plan['source_snapshot_census']['sha256'])
overlay=doc(plan['source_overlay']['path'],plan['source_overlay']['sha256'])
expected={n:(r['frozen_sha256'],r['frozen_bytes']) for n,r in census['rows'].items()}
assert len(expected)==238 and sum(v[1] for v in expected.values())==2150761 and len(overlay['files'])==5
for n,r in overlay['files'].items():
    assert r['original_sha256']==expected[n][0]
    expected[n]=(r['sha256'],r['bytes'])
assert set(expected)==set(plan['source_materialization'])
assert {str(p.relative_to(PREFIX)) for p in PREFIX.rglob('*') if p.is_file()}==set(expected)
for n,(digest,size) in expected.items():
    row=plan['source_materialization'][n]
    assert row['path']==str(PREFIX/n) and row['sha256']==digest and row['bytes']==size
    check_ref(row)
    assert row==plan['files'][row['path']] and row['identity']==plan['memberships'][str(PREFIX)][n]
    assert row['identity'][6]==1
assert sum(v[1] for v in expected.values())==receipt['outputs']['source_bytes']==2154094
assert receipt['outputs']['source_files']==238
selection_path=O/'.work/exporter-d2-b3-saved-provider-route-assessment-01.json'
selection=doc(selection_path,plan['files'][str(selection_path)]['sha256'])
private_path=Path(roles['private_sysroot_manifest']['path'])
private=doc(private_path,roles['private_sysroot_manifest']['sha256'])
ready_path=RUNTIME.parent/'ready.json'
ready=doc(ready_path,plan['files'][str(ready_path)]['sha256'])
groups={str(D2):{str(Path(n).relative_to(D2)):r['sha256'] for n,r in selection['d2_full_saved_rows'].items()},str(B3):private['files'],str(RUNTIME):ready['identity']['files']}
assert [len(groups[str(p)]) for p in (D2,B3,RUNTIME)]==[148,335,3708]
for root,table in groups.items():
    assert set(plan['memberships'][root])==set(table)
    for n,digest in table.items():
        row=plan['files'][str(Path(root)/n)]
        assert row['sha256']==digest and row['identity']==plan['memberships'][root][n]
assert roles['runtime']['executable']==dict(path=str(RUNTIME/'bin/rustc'),sha256=ready['identity']['files']['bin/rustc'])
assert roles['runtime']['verbose_version']==ready['identity']['compiler'] and roles['runtime']['default_sysroot']==str(RUNTIME)
assert roles['runtime_source_commit']==ready['identity']['provenance']['source_commit']
assert private['runtime_source_commit']==roles['runtime_source_commit'] and private['build_compiler_sha256']==roles['build']['executable']['sha256']
old_path=X/'experiments/runtime-exporter/metadata-02/plan.json'
old=doc(old_path,plan['files'][str(old_path)]['sha256'])
assert plan['registry_packages']==old['registry_packages'] and len(plan['registry_packages'])==26
assert plan['routes']==old['routes'] and plan['adopted_VM']==old['future_VM']
for path,row in old['registry_files'].items():assert plan['files'][path]['sha256']==row['sha256']
for package in plan['registry_packages']:
    root=Path(package['manifest_path']).parent;table=plan['memberships'][str(root)]
    assert {str(root/n) for n in table}==set(package['source_files'])
    for n,s in table.items():assert plan['files'][str(root/n)]['identity']==s
assert len(plan['memberships'])==30
assert plan['runtime_qualification']==receipt['runtime']
for r in receipt['runtime'].values():
    read(r['path'],r['sha256']);assert refs[r['path']]==plan['files'][r['path']]
audit=json.loads(read(receipt['runtime']['audit']['path']))
audit_execution=json.loads(read(receipt['runtime']['execution']['path']))
assert audit['status']=='verified' and audit['phase_result']['runtime_key']==KEY and audit['phase_result']['ready_sha256']==refs[str(ready_path)]['sha256']
assert audit_execution['returncode']==0 and audit_execution['may_be_live'] is False
assert audit['pid']==audit_execution['pid'] and audit['parent_pid']==audit_execution['parent_pid']
assert audit_execution['result_sha256']==receipt['runtime']['audit']['sha256']
env=plan['launch_environment'];be=plan['build_environment'];flags=roles['build_rustflags']
assert be==env|dict(RUSTC=str(D2/'bin/rustc'),RUSTDOC=str(D2/'bin/rustdoc'),RUSTC_BOOTSTRAP='1',RUST_INTERP_COMPILER_ROLES=str(P/'compiler-roles.json'),CARGO_ENCODED_RUSTFLAGS='\x1f'.join(flags))
assert env['TMPDIR']==str(WORK/'tmp')+'/' and env['__CF_USER_TEXT_ENCODING'].split(':')[0].lower()==hex(os.getuid())
assert not any(n in be for n in ('RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_INTERP_HOST_CODEGEN_OPT'))
cargo=old['support_executables']['cargo'];sdk=[]
for row in old['children']:
    if row['argv'][0] in ('/usr/bin/xcode-select','/usr/bin/xcrun') and row['argv'] not in sdk:sdk.append(row['argv'])
previous_path=X/'.work/runtime-exporter-metadata-01/receipt.json'
previous=doc(previous_path,plan['files'][str(previous_path)]['sha256'])
children=[]
def add(label,argv,environment=env,cwd=X,stdout=None):children.append(dict(label=label,command=argv,environment=environment,cwd=str(cwd),expected=[0],expected_stdout_sha256=stdout))
sdk_shas={}
for argv in sdk:
    r=next(v for v in previous['commands'] if v['command']==argv)
    d=doc(r['path'],r['sha256']);assert d['status']=='finished' and d['returncode']==0 and d['command']==argv
    sdk_shas[tuple(argv)]=d['stdout_sha256']
for i,argv in enumerate(sdk):add('sdk-'+str(i),argv,stdout=sdk_shas[tuple(argv)])
binaries=[str(D2/'bin/rustc'),str(RUNTIME/'bin/rustc'),*old['support_executables'].values()]
assert plan['loader_binaries']==binaries
libraries=sorted(p for p in plan['files'] if (Path(p).parent in (D2/'lib',RUNTIME/'lib') and (Path(p).name.startswith('librustc_driver-') or Path(p).name=='libLLVM.dylib')) or p.startswith('/opt/homebrew/') and Path(p).name=='Python')
for path in sorted(set(binaries+libraries)):
    for flag in ('-L','-l'):add('loader-'+str(len(children)),['/usr/bin/otool','-arch','arm64',flag,path])
for name in ('build','runtime'):
    path=roles[name]['executable']['path'];add(name+'-version',[path,'-vV'],env|{'DYLD_PRINT_LIBRARIES':'1'});add(name+'-sysroot',[path,'--print','sysroot'])
add('cargo-version',[cargo,'-Vv'])
add('cargo-metadata',[cargo,'metadata','--locked','--offline','--format-version=1','--manifest-path',str(PREFIX/'Cargo.toml')],be|{'CARGO_TARGET_DIR':str(WORK/'cargo-target')},PREFIX)
for i,argv in enumerate(sdk):add('sdk-after-'+str(i),argv,stdout=sdk_shas[tuple(argv)])
assert children==plan['children'] and len(children)==receipt['outputs']['metadata_children']==36
assert plan['metadata_target']==str(WORK/'cargo-target')
assert plan['future_build']==dict(command=[cargo,'build','--release','--locked','--offline','--jobs','2','-vv','--message-format=json-render-diagnostics','--manifest-path',str(PREFIX/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-mir-export','--bin','rust-interp-mir-export','--bin','rust-interp-rustc-wrapper'],cwd=str(PREFIX),environment=be|{'TMPDIR':str(X/'.work/host-wrapper-exporter-build-01/tmp')+'/'},exporter_builds=1,compiler_builds=0,VM_builds=0)
for p,row in list(refs.items()):read(p,row['sha256']);assert refs[p]==row
out=A/'.work/host-wrapper-exporter-preparation-independent-readback-01.json'
report=dict(status='verified',scope='closed preparation packet/current source bytes/provider declarations only',parent=refs[str(parent_path)],receipt=refs[parent['receipt']['path']],packet={n:refs[str(P/n)] for n in ('plan.json','inputs.json','launch.json','compiler-roles.json')},owned_parent_pid=93279,owned_child_pid=94000,returncode=0,source_files=238,source_bytes=2154094,overlay_files=5,current_source_rows=17,declared_input_files=5685,declared_input_bytes=sum(v['bytes'] for v in plan['files'].values()),provider_declarations=dict(D2=148,B3=335,runtime=3708,registry_packages=26),metadata_children=36,complete_recipe_reconstructed=True,full_provider_payload_walk_repeated=False,SDK_payload_walk_repeated=False,source_payloads_read=True,provider_table_currentness='Original closed preparation performed full payload and membership checks; this readback checks declarations against bound saved metadata only.',capacity=plan['capacity'],entry_free_bytes=receipt['entry_free_bytes'],free_bytes_after=receipt['free_bytes_after'],active_phase_outputs_read=False,metadata_execution_state="Root owns subsequent metadata execution; this readback makes no metadata result claim.",exporter_qualified=False,on_mode_application_qualified=False,performance_qualified=False,references=list(refs.values()),reader=dict(path=__file__,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
assert not out.exists()
out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size,refs=len(refs))))

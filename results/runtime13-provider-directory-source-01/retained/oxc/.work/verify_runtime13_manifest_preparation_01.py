"""Bounded independent saved preparation readback; build an unexecuted audit argv."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import stat
import time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
H=ROOT/'experiments/hir-options-hash-runtime-audit-13'
S=ROOT/'experiments/runtime-installation-after-preflight05-03'
M=ROOT/'.work/runtime13-saved-audit-installation-manifest-01'
E=ROOT/'.work/runtime13-saved-audit-installation-manifest-preparation-execution-01'
INV=ROOT/'.work/runtime13-saved-audit-source-inventory-01.json'
CENSUS=O/'.work/runtime13-prospective-supplemental-census-01.json'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
OBSERVED={}


def identity(st):
    return {name:getattr(st,'st_'+name) for name in FIELDS}


def raw(path, expected=None):
    path=Path(path)
    assert path.is_absolute() and path.resolve(strict=True)==path
    before=identity(path.lstat())
    assert stat.S_ISREG(before['mode']) and before['size']<=10*2**20
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
        assert identity(os.fstat(f.fileno()))==before
        data=f.read(10*2**20+1)
        assert identity(os.fstat(f.fileno()))==before
    assert identity(path.lstat())==before and len(data)==before['size']
    row=dict(identity=before,size=len(data),sha256=hashlib.sha256(data).hexdigest())
    assert expected is None or row['sha256']==expected
    assert str(path) not in OBSERVED or OBSERVED[str(path)]==row
    OBSERVED[str(path)]=row
    return data


def same(a,b):
    return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)


def read(path, expected=None):
    def unique(pairs):
        value={}
        for key,item in pairs:
            assert key not in value
            value[key]=item
        return value
    return json.loads(raw(path,expected),object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def ref(path):
    return dict(path=str(path),**OBSERVED[str(path)])


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*2**20,4*2**20))
    started=time.time()
    rec=read(E/'record.json','0b73ce43a4e9f2fab103ff9cf2e124380daa00a5a219103002de3847e6828bc2')
    prep=read(M/'preparation.json','e23f5df3dd4f962b96b127d2bc9293befd0732fd9d67aebbd4d6bc6a4d65a495')
    manifest=read(M/'manifest.json','22b62cf3de500e0bd6d5ad4b6d465c3b803eda25889df8d3da3b7366593bb2e4')
    inv=read(INV,'2286f48fcb8e41c8f50138a592a1500f73095c8b9abaa67aed5c47a2abbe1cbd')
    census=read(CENSUS,'a7bd8f89311f02051b59763d128e1449855087484c10d4f7832dafb199bd7b8a')
    assert set(p.name for p in E.iterdir())=={'record.json','stdout','stderr','source.py','execution.py','owned_stage.py','source-inventory.json','invocation.json'}
    assert set(p.name for p in M.iterdir())=={'manifest.json','preparation.json'}
    trees={str(d):{p.name:identity(p.lstat()) for p in d.iterdir()} for d in [E,M]}
    assert set(manifest)=={'policy','files','actual53','phase45','preparation','preparation_launcher','startup_controls','retry_controls','frozen_links_controls','installation_controls','native_loader_controls','source_preflight_audit'}
    assert manifest['policy']=='runtime07-installation-native-loader-saved-audit-source-manifest-v1'
    assert same(manifest['files'],census['files'])
    assert len(manifest['files'])==prep['files']==326
    assert sum(v['size'] for v in manifest['files'].values())==prep['logical_bytes']==7185333<=8*2**20
    for name,row in manifest['files'].items():
        raw(name,row['sha256'])
        assert same(OBSERVED[name],row),name
    assert inv['policy']=='runtime13-reviewed-sources-v1' and len(inv['sources'])==30
    for name,expected in inv['sources'].items():
        assert manifest['files'][name]['sha256']==expected
    assert same(read(E/'source-inventory.json'),inv)
    assert raw(E/'source.py',rec['source_sha256'])==raw(H/'prepare_manifest.py')
    assert raw(E/'execution.py',rec['execution_source_sha256'])==raw(H/'execute.py')
    raw(E/'owned_stage.py','7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e')
    invocation=read(E/'invocation.json')
    assert invocation['mode']=='prepare' and invocation['phase']=='installation'
    assert invocation['source_inventory']==str(INV) and invocation['source_inventory_sha256']==OBSERVED[str(INV)]['sha256']
    assert invocation['runtime_preparation_sha256']==manifest['preparation']['sha256']=='61fe20cc4533fdff67f6336b62bc4bd0bf324a6c5d44ef6bf207ca716e0f39ce'
    assert invocation['runtime_preparation_launcher_sha256']==manifest['preparation_launcher']['sha256']=='ab0609d297302262feb418a240d0ec4a0c88d511f73e381c0a5c5b4245473c68'
    assert rec['status']=='finished' and type(rec['returncode']) is int and rec['returncode']==0
    assert rec['may_be_live'] is False and rec['observation_errors']==[]
    assert not any(key in rec for key in ['execution_error','publication_error','initial_publication_error'])
    assert rec['mode']=='prepare' and rec['phase']=='installation' and rec['cwd']==str(R)
    assert rec['pid']==prep['pid']==74072 and rec['parent_pid']==prep['parent_pid']==73356
    assert rec['started_at']<=rec['admitted_at']<=rec['child_started_at']<=prep['finished_at']<=rec['finished_at']<=rec['canonical_released_at']<=time.time()
    assert rec['admitted_at']-rec['started_at']<=rec['wait_seconds']==600
    assert rec['finished_at']-rec['child_started_at']<=1250
    assert rec['capacity']==dict(entry_gib=16,live_gib=9,floor_gib=8)
    assert rec['maximum_manifest_rows']==368 and rec['maximum_manifest_payload_bytes']==8*2**20
    for key in ['runtime_admission','retirement_authorized']:
        assert rec[key] is prep[key] is False
    for key in ['compiler_calls','provider_probes','process_signals','network_calls']:
        assert rec[key]==prep[key]==0
    assert prep['status']=='prepared-audit-source-manifest' and prep['phase']=='installation'
    assert prep['manifest']==dict(path=str(M/'manifest.json'),sha256=OBSERVED[str(M/'manifest.json')]['sha256'])
    assert rec['result_sha256']==OBSERVED[str(M/'preparation.json')]['sha256'] and rec['manifest_sha256']==prep['manifest']['sha256']
    assert same(prep['source_inventory'],rec['source_inventory']) and prep['source_inventory']==dict(path=str(INV),sha256=OBSERVED[str(INV)]['sha256'])
    assert [row.get('controls',row.get('tests')) for row in prep['controls']]==[53,45,39,33,25,48,24]
    assert raw(E/'stderr',rec['stderr_sha256'])==b''
    stdout=read(E/'stdout',rec['stdout_sha256'])
    assert stdout==dict(status=prep['status'],manifest=prep['manifest'],preparation=dict(path=str(M/'preparation.json'),sha256=rec['result_sha256']))
    routes=read(S/'routes.json','d339e74a11edb948f3cf4bcc0afbbba76887cc61aed125c8bb8bf62b1633723a')
    packet=Path(routes['packet']);work=Path(routes['work']);outerdir=Path(routes['supervisor']);launcherdir=Path(routes['launcher_execution'])
    paths={'launch':packet/'launch.json','inputs':packet/'inputs.json','snapshot-plan':packet/'snapshot-plan.json',
           'receipt':work/'receipt.json','result':work/'source-probe/result.json','outer':outerdir/'status.json','launcher-record':launcherdir/'record.json'}
    values={name:read(path) for name,path in paths.items()}
    terminal=values['receipt'];outer=values['outer'];launcher=values['launcher-record'];launch=values['launch'];result=values['result']
    assert terminal['status']=='passed' and terminal['phase']=='installation' and len(terminal['children'])==15
    assert outer['status']=='finished' and type(outer['returncode']) is int and outer['returncode']==0
    assert launcher['status']=='terminal-observed' and launcher['returncode']==launcher['launcher_returncode']==0
    assert launcher['outer_sha256']==OBSERVED[str(paths['outer'])]['sha256'] and launcher['launch_sha256']==OBSERVED[str(paths['launch'])]['sha256']
    assert terminal['pid']==outer['child_pid']==launcher['controller_pid']==83231
    assert terminal['parent_pid']==outer['supervisor_pid']==launcher['supervisor_pid']==83187
    assert terminal['finished_at']<=outer['finished_at']<=launcher['terminal_observed_at']
    assert terminal['inputs_sha256']==launch['inputs_sha256']==OBSERVED[str(paths['inputs'])]['sha256']
    assert terminal['snapshot_plan_sha256']==launch['snapshot_plan_sha256']==OBSERVED[str(paths['snapshot-plan'])]['sha256']
    assert launcher['command']==launch['command'] and launch['command'][5]=='--'
    assert outer['command']==launch['command'][6:]
    assert result['status']=='passed' and result['pid']==83231 and result['parent_pid']==83187
    assert result['key']==terminal['installed_runtime_key']==terminal['runtime_key']=='f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
    assert result['sysroot']==terminal['sysroot'] and result['finished_at']<=terminal['finished_at']
    assert result['application_qualified'] is result['std_mir_prepared'] is result['full_presentation_qualified'] is False
    for stream in ['stdout','stderr']:
        raw(launcherdir/stream,launcher[stream+'_sha256'])
    assert raw(launcherdir/'stderr')==b''
    assert raw(launcherdir/'launcher.py',launcher['launcher_source_sha256'])==raw(S/'launch.py')
    for name,row in prep['runtime_preparation']['declared_packet_outputs'].items():
        raw(packet/name,row['sha256']);assert same(OBSERVED[str(packet/name)],row)
    raw(outerdir/'command.log',outer['log_sha256'])
    source_preflight=manifest['source_preflight_audit']
    assert same(prep['source_preflight_audit'],source_preflight)
    assert source_preflight['sha256']=='e2ec858a1e52e6b7573807d8834673699efcdf29ccdd801a84a973322cd9179a'
    argv=['/opt/homebrew/bin/python3','-B',str(H/'execute.py'),'audit',
          '--source-inventory',str(INV),'--source-inventory-sha256',OBSERVED[str(INV)]['sha256'],
          '--phase','installation','--source-preflight-audit-sha256',source_preflight['sha256'],
          '--manifest-sha256',OBSERVED[str(M/'manifest.json')]['sha256'],
          '--preparation-sha256',OBSERVED[str(M/'preparation.json')]['sha256'],
          '--preparation-record-sha256',OBSERVED[str(E/'record.json')]['sha256']]
    for name,path in paths.items():argv.extend(['--'+name+'-sha256',OBSERVED[str(path)]['sha256']])
    future_execution=ROOT/'.work/runtime13-saved-audit-installation-execution-01'
    # Root may have launched the reviewed command concurrently; do not read its active outputs.
    for name,row in OBSERVED.items():assert identity(Path(name).lstat())==row['identity'],name
    assert {str(d):{p.name:identity(p.lstat()) for p in d.iterdir()} for d in [E,M]}==trees
    report=dict(status='verified-actual-manifest-preparation-concrete-audit-command-unexecuted',
        pid=os.getpid(),parent_pid=os.getppid(),started_at=started,finished_at=time.time(),
        manifest=ref(M/'manifest.json'),preparation=ref(M/'preparation.json'),execution=ref(E/'record.json'),
        source_inventory=ref(INV),source_inventory_files=30,actual326_rows_equal_independent_census=True,
        actual326_payloads_rehashed=True,logical_bytes=7185333,source_rows=manifest['files'],
        independent_census=ref(CENSUS),source_route_replacements=census['replacement_routes'],
        preparation_parent=73356,preparation_child=74072,preparation_closed_returncode=0,
        preparation_outputs=trees,source_and_raw_associations_verified=True,
        named_nonworkspace_source_dependencies=[name for name in manifest['files'] if not name.startswith('/Users/danluu/dev/rust-interp')],
        binary_execution=False,provider_payload_walk=False,phase_dependencies={name:ref(path) for name,path in paths.items()},
        phase_scope='Exact saved closure and command-pin readback only; full installed prefix/provider/child audit remains the future saved-audit child and A independent runtime review.',
        runtime_parent=83187,runtime_controller=83231,runtime_children_declared=15,
        command=argv,shell_command=shlex.join(argv),cwd=str(R),future_execution=str(future_execution),future_report=routes['report'],
        future_report_sha256=None,executed_audit=False,source_mutations=False,
        observed_files=len(OBSERVED),compiler_calls=0,provider_calls=0,target_imports=0)
    dest=O/'.work/runtime13-manifest-preparation-independent-readback-01.json'
    data=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode()
    with dest.open('xb') as f:f.write(data)
    print(json.dumps(dict(path=str(dest),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),command=argv)))


if __name__=='__main__':main()

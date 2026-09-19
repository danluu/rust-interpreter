"""Read-only bounded discovery of one failed prefix; writes an unrun proposal."""
import ast
import json
import os
from pathlib import Path
import sys
import retire as r

CONTROL_SOURCE=r.A/'experiments/ruff-strict-cache-retirement-01'
CONTROL_RECEIPT=r.A/'.work/ruff-strict-cache-retirement-controls-01/receipt.json'
CONTROL_AUDIT=r.O/'.work/ruff-strict-cache-retirement-controls-independent-verification-01.json'
PROVIDER_PROOF=r.X/'experiments/hir-options-hash/runtime-installation-handoff-01/provider-comparison.json'


def main():
    r.require(Path.cwd()==r.OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed preparer owner required')
    r.require(not r.PACKET.exists() and not r.WORK.exists()
        and not (r.OWNER/'.work/experiments/old-compiler-partial-retirement-supervisor-01').exists(),'fresh namespaces required')
    r.capacity();comparison=r.read(r.COMPARISON);rows=r.inventory(r.TARGET)
    r.require(rows==r.compared_rows(),'current target no longer matches exact comparison')
    history=r.archive_history();files={};routes={};directories={}
    def add(path,expected=None,original_identity=None):
        path=Path(path);target=path.resolve(strict=True)
        r.require(not target.is_relative_to(r.TARGET),'mutable retirement payload may not enter immutable closure')
        routes[str(path)]=dict(resolved=str(target),identity=r.identity(path));row=r.file(target)
        if expected is not None:r.require(row['sha256']==expected,'retained byte proof differs: '+str(path))
        if original_identity is not None:r.require(row['identity']==original_identity,'retained identity proof differs: '+str(path))
        r.require(str(target) not in files or files[str(target)]==row,'inconsistent frozen identity')
        files[str(target)]=row
        r.require(len(files)<=30000 and sum(v['identity']['size'] for v in files.values())<=5*r.GIB,'input discovery count/byte bound')
        if target.suffix=='.py':ast.parse(target.read_text(),filename=str(target))
    def tree(path):
        path=Path(path)
        r.require(path.resolve(strict=True)==path,'indirect proof root')
        for parent,dirs,names in os.walk(path,followlinks=False):
            for name in dirs:r.require(not (Path(parent)/name).is_symlink(),'indirect proof directory')
            for name in names:add(Path(parent)/name)
    def directory(path,expected=None):
        path=Path(path);r.require(path.resolve(strict=True)==path and path.is_dir(),'ordinary protected directory required')
        value=r.identity(path)
        if expected is not None:r.require(value==expected,'historical protected directory changed')
        directories[str(path)]=dict(identity=value,children=sorted(os.listdir(path)))
    # Both already published payload sets are immutable protected inputs. They
    # remain wholly outside the one writable staging tree selected for removal.
    for path,row in comparison['preserved_files'].items():add(path,row['sha256'],row['identity'])
    add(r.PRESERVED/'ready.json',comparison['preserved_ready']['sha256'],comparison['preserved_ready']['identity'])
    published=comparison['targets'][str(r.PUBLISHED)]
    for path,row in published['files'].items():add(path,row['sha256'],row['identity'])
    directory(r.PRESERVED);directory(r.PUBLISHED,published['root_identity'])
    for name,row in published['members'].items():
        if row['kind']=='directory':directory(r.PUBLISHED/name,row['identity']);directory(r.PRESERVED/name)
    provider=r.read(PROVIDER_PROOF);add(PROVIDER_PROOF)
    source=Path(provider['source_distribution']['provider'])
    for name,row in provider['source_distribution']['provider_files'].items():add(source/name,row['sha256'])
    add(provider['support']['path'],provider['support']['file']['sha256'])
    f9=source.parents[5];r.require(f9.parent==r.TARGET.parent and f9.name.startswith('f9fb3e5f'),'retained source-provider root differs')
    directory(f9);directory(source)
    # Preserve selected current compiler/runtime executable/provider bytes and
    # all 335 new B3 payloads through their actual current inventories.
    n=r.X/'.work/hir-options-hash-compiler-01';s=n/'source';host='aarch64-apple-darwin'
    for sysroot in [s/'build'/host/'stage0',s/'build'/host/'stage1']:
        directory(sysroot);add(sysroot/'bin/rustc')
        drivers=list((sysroot/'lib').glob('librustc_driver-*.dylib'));r.require(len(drivers)==1,'current compiler driver ambiguous')
        for path in [drivers[0],sysroot/'lib/libLLVM.dylib']:add(path)
    directory(n/'beta-sysroot')
    b3=r.A/'.work/hir-options-hash-beta-composition-08/assembly/output-inventory.json';add(b3)
    for name,row in r.read(b3).items():add(n/'beta-sysroot'/name,row['sha256'],row['identity'])
    # Fixed existing actual/frozen consumers are scanned for the exact target,
    # including any string embedded inside a copied historical input catalog.
    consumer_records=[];consumer_absences=[]
    for source_root in [r.A/'experiments/hir-options-hash-beta-composition-08',
                        r.A/'experiments/hir-options-hash-native-controls-01',
                        r.O/'experiments/hir-options-hash-run-make-stage-02']:
        for name in ['plan.json','inputs.json','launch.json']:
            path=source_root/name;r.require(path.is_file(),'actual consumer packet required')
            r.require(not r.contains_target(r.read(path)),'current consumer references retired prefix');add(path);consumer_records.append(str(path))
    for name in ['plan.json','inputs.json','launch.json']:
        path=r.OWNER/'experiments/hir-options-hash-driver-stage'/name
        if path.exists():
            r.require(not r.contains_target(r.read(path)),'hash stage references retired prefix');add(path);consumer_records.append(str(path))
        else:consumer_absences.append(str(path))
    for path in [r.COMPARISON,CONTROL_AUDIT,CONTROL_RECEIPT,
        r.OWNER/'.work/verify_old_compiler_failure_archive_02.py',r.OWNER/'scripts/supervise_experiment.py',
        r.OWNER/'experiments/stable-cgu/owned_stage.py',r.A/'experiments/runtime-application-admission/runtime_platform.py',
        r.A/'.work/beta-composition-independent-verification-08.json',r.A/'.work/verify_beta_composition_08_loader_projection_02.py',
        r.O/'.work/verify_ruff_strict_cache_controls_01.py']:
        add(path)
    tree(r.HISTORY);tree(CONTROL_SOURCE/'controls-01')
    for path in [r.A/'.work/ruff-strict-cache-retirement-controls-01',
        r.A/'.work/experiments/ruff-strict-cache-retirement-controls-supervisor-01']:tree(path)
    for path in r.HERE.iterdir():
        if path.is_file():add(path)
    for name in ['fd_remove.py','test_fd_remove.py','bounded_probes.py']:add(CONTROL_SOURCE/name)
    r.require(r.sha(r.HERE/'fd_remove.py')==r.sha(CONTROL_SOURCE/'fd_remove.py')
        =='0b154792e3b393bdc018a6ee4337347535be466db64aa3fa40cd6a3899be6041','qualified removal source differs')
    python=Path(sys.executable).resolve(strict=True)
    for path in [python,'/opt/homebrew/bin/python3','/bin/ps','/usr/sbin/lsof']:add(path)
    environment=dict(HOME='/Users/danluu',USER='danluu',LOGNAME='danluu',LANG='C',LC_ALL='C',TZ='UTC',
        PATH='/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',__CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
    commands=[dict(label='open-handles',argv=['/usr/sbin/lsof','+D',str(r.TARGET)],expected=[0,1]),
        dict(label='closed-owner-pids',argv=['/bin/ps','-p',','.join(map(str,history['closed_pids'])),
            '-o','pid=,ppid=,pgid=,lstart=,tty=,command='],expected=[0,1])]
    transition=dict(action='retire-single-closed-failed-staging-prefix',root=str(r.TARGET),
        historical_comparison=dict(path=str(r.COMPARISON),sha256=r.sha(r.COMPARISON)),
        historical_summary=dict(path=str(r.HISTORY/'summary.json'),sha256=r.sha(r.HISTORY/'summary.json')),
        archive=dict(path=str(r.HISTORY/'evidence.tar.xz'),sha256=r.sha(r.HISTORY/'evidence.tar.xz')),
        actual_archive_audit=dict(path=str(r.HISTORY/'full-archive-verification-02.json'),sha256=r.sha(r.HISTORY/'full-archive-verification-02.json')),
        files=6982,directories=1406,entries=8388,preserved_equal_payload_root=str(r.PRESERVED),chmod=False,
        preserved_publication_mode_difference='Original staging modes and all byte identities remain in comparison03; retained publication has intentional installer-mode transformation.',
        history_meaning='The original failed attempt remains failed and its staging prefix is absent only after an actually passing retirement receipt.')
    plan=dict(status='prepared-unrun',owner=str(r.OWNER),root=str(r.TARGET),work=str(r.WORK),python=str(python),environment=environment,
        routes=dict(routes),platform_identity=r.runtime_platform.identity(list(os.uname())),platform_context=r.runtime_platform.observation(list(os.uname())),
        commands=commands,closed_history=history,controls=dict(receipt=str(CONTROL_RECEIPT),audit=str(CONTROL_AUDIT),inputs=str(CONTROL_SOURCE/'controls-01/inputs.json'),tested_helper=str(CONTROL_SOURCE/'fd_remove.py')),
        protected_directories=directories,outer_identity=r.identity(r.TARGET.parent),outer_children=sorted(os.listdir(r.TARGET.parent)),
        consumer_records=consumer_records,consumer_absences=consumer_absences,transition=transition,
        observed_allocated_bytes=comparison['targets'][str(r.TARGET)]['allocated_bytes'],
        bounds=dict(entry_free_bytes=9*r.GIB+256*r.MIB,live_free_gib=9,floor_gib=8,evidence_bytes=256*r.MIB,
            ledger_bytes=192*r.MIB,canonical_wait_seconds=600,inputs=30000,input_bytes=5*r.GIB,single_input_bytes=512*r.MIB,
            inventory_entries=10000,inventory_logical_bytes=2*r.GIB),
        limitations=['Only exact closed staging directory is removable; published e48 and completed600/f9/std/tool roots remain.',
            'Read-only historical PID absence probe fails on any reused PID; no process signal or ownership inference.',
            'Complete retained600/e48 payloads and source provider files are rehashed; selected current D2/E2/B3 providers are guarded, not a whole-host claim.'])
    r.PACKET.mkdir();r.owned.write(r.PACKET/'inventory.json',rows);r.owned.write(r.PACKET/'plan.json',plan)
    add(r.PACKET/'inventory.json');add(r.PACKET/'plan.json')
    freeze=dict(status='prepared-unrun',files=files,plan_sha256=r.sha(r.PACKET/'plan.json'))
    r.owned.write(r.PACKET/'inputs.json',freeze)
    launch=dict(status='prepared-unrun-awaiting-exact-review',command=[str(python),'-B',str(r.OWNER/'scripts/supervise_experiment.py'),
        '--run-id','old-compiler-partial-retirement-supervisor-01','--',str(python),'-B',str(r.HERE/'retire.py'),
        '--inputs-sha256',r.sha(r.PACKET/'inputs.json')],cwd=str(r.OWNER),environment=environment,
        inputs_sha256=r.sha(r.PACKET/'inputs.json'),helper_sha256=r.sha(r.HERE/'retire.py'),bounds=plan['bounds'],actual_readonly_probes=2,removed_entries=8388)
    r.owned.write(r.PACKET/'launch.json',launch)
    check=object.__new__(r.Retirement);check.plan=plan;check.freeze=freeze;check.guard();check.protected()
    r.require(r.inventory(r.TARGET)==rows,'target changed during read-only discovery')
    print(json.dumps(dict(status='prepared-unrun',launch_sha256=r.sha(r.PACKET/'launch.json'),inputs_sha256=r.sha(r.PACKET/'inputs.json'),
        files=len(files),bytes=sum(row['identity']['size'] for row in files.values()),removed_entries=8388),indent=2))


if __name__=='__main__':main()

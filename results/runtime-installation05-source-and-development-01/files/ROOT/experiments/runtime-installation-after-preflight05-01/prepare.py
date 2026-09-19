"""Read-only runtime discovery from four actual audits; no provider execution.

Source draft only. Canonical24/9 admission precedes all provider discovery and
proposal writes. This fresh attempt admits only installation24/9/8; completed preflight05 remains immutable.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import entry
import frozen as f
import imports as factory

# This separately authenticated artifact retains the qualified packet/import
# owner. The enclosing preparation wrapper supplies only this exact module path.
HERE=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/experiments/hir-options-hash/runtime-installation-04')
ADAPTER=Path(__file__).resolve().parent
STARTUP_SOURCE=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01')
f.require(entry.HERE==HERE and entry.ATTEMPT==ADAPTER and Path(entry.__file__).resolve()==ADAPTER/'entry.py'
    and Path(f.__file__).resolve()==HERE/'frozen.py'
    and Path(factory.__file__).resolve()==HERE/'imports.py','exact qualified producer module routes required')
R=entry.R
X=HERE.parents[2]
ROOT=entry.HASH_SOURCE.parents[1]
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
COMPILED=X/'.work/hir-options-hash-compiler-build-continuation-03/compiled.json'
PROVIDER=HERE.parent/'runtime-installation-handoff-01/provider-comparison.json'
REMAP=O/'.work/native-build-remap-proof-01.json'
OLD_SPEC=R/'experiments/runtime-compiler-installation/final-r-02/specification.json'
OLD_POLICY=R/'experiments/runtime-compiler-installation/final-r-01/source-policy-proof.json'
CONTROLS=O/'experiments/runtime-adapter-controls-01'
CONTROL_WORK=O/'.work/runtime-adapter-controls-01'
CONTROL_AUDIT=O/'.work/runtime-adapter-controls-independent-verification-01.json'
STARTUP_CONTROLS=ROOT/'experiments/runtime-startup-environment-controls-01'
STARTUP_WORK=ROOT/'.work/runtime-startup-environment-controls-01'
STARTUP_AUDIT=ROOT/'.work/runtime-startup-environment-controls-independent-verification-01.json'
STARTUP_CONTROL_COUNT=39  # 24 startup/Controller admission + 15 complete owner controls; actual proof required.
STARTUP_FILES={'environment.py','prepare.py','test_environment.py','audit_owner.py',
    'test_audit_owner.py','source-bindings.json','README.md'}


def write(path,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    f.require(len(data)<=256*2**20,'bounded discovery JSON required')
    with Path(path).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['installation'],required=True)
    for role in ['beta','native','run-make','hash']:
        parser.add_argument('--'+role+'-audit',type=Path,required=True);parser.add_argument('--'+role+'-audit-sha256',required=True)
        parser.add_argument('--'+role+'-evidence',type=Path,required=True)
    parser.add_argument('--source-preflight-audit',type=Path);parser.add_argument('--source-preflight-audit-sha256')
    parser.add_argument('--copy-retirement-audit',type=Path,required=True)
    parser.add_argument('--copy-retirement-audit-sha256',required=True)
    parser.add_argument('--startup-audit-sha256',required=True)
    parser.add_argument('--retry-audit-sha256',required=True)
    parser.add_argument('--installation-audit-sha256',required=True)
    parser.add_argument('--preparation-passed-environment-json',required=True)
    parser.add_argument('--preparation-record',type=Path,required=True)
    parser.add_argument('--startup-source-manifest',type=Path,required=True)
    parser.add_argument('--startup-source-manifest-sha256',required=True)
    args=vars(parser.parse_args())
    startup_observations=dict(before_factory_definitions=dict(os.environ))
    f.require(type(STARTUP_CONTROL_COUNT) is int and STARTUP_CONTROL_COUNT>0,
        'startup source/control count remains unbound')
    f.require(sys.platform=='darwin' and os.getuid()==501,'existing Darwin owner required')
    f.require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'fixed R preparer context required')
    audits={}
    works={role:args[role+'_evidence'] for role in ['beta','native','run_make','hash']}
    # No candidate discovery/import can turn a future source proposal into an
    # actual prerequisite. All four terminals/audits must already exist.
    for role,work in works.items():
        path,digest=args[role+'_audit'],args[role+'_audit_sha256']
        proof=f.json_file(path);terminal=f.json_file(work/'receipt.json')
        f.require(len(digest)==64 and f.digest(path)==digest and proof['status']=='verified'
            and proof['receipt_sha256']==f.digest(work/'receipt.json')
            and terminal['status']==('passed-awaiting-independent-audit' if role=='hash' else 'passed'),
            'actual completed independent prerequisite required: '+role)
        audits[role]=dict(path=str(path),sha256=digest)
    routes=entry.attempt_routes(read_json=f.json_file,sha=f.digest)
    phase=args['phase'];packet=Path(routes['packet']);work=Path(routes['work'])
    supervisor=Path(routes['supervisor']);launcher_work=Path(routes['launcher_execution'])
    preparation_record=Path(routes['preparation_execution'])/'record.json'
    f.require(type(entry.RETRY_CONTROL_COUNT) is int and entry.RETRY_CONTROL_COUNT>0,
        'focused retry source/control count remains unbound')
    f.require(args['preparation_record']==preparation_record,'exact current preparation record route required')
    f.require(all(not p.exists() and not p.is_symlink() for p in [packet,work,supervisor,launcher_work]),'fresh runtime proposal/output required')
    checked_sources={}
    def precheck(path):
        path=Path(path);ast.parse(path.read_text(),filename=str(path))
        row=dict(sha256=f.digest(path),identity=f.identity(path),size=path.stat().st_size)
        f.require(str(path) not in checked_sources or checked_sources[str(path)]==row,'imported source changed')
        checked_sources[str(path)]=row
    modules=factory.definitions(entry.HASH_SOURCE,precheck)
    startup_observations['after_factory_definitions']=dict(os.environ)
    expected_works=dict(beta=modules.stage.BETA_WORK,native=modules.stage.NATIVE_QUALIFICATION_WORK,
        run_make=modules.stage.RECIPE_WORK,hash=modules.stage.WORK)
    f.require(works==expected_works,'explicit evidence differs from actual adopted hash prerequisite roles')
    d=entry.discovery(modules)
    with d.owned.workload_lock(d.owned.CANONICAL_LOCK,600):
        started=time.time();free_before=d.owned.disk(R,24)
        f.require(all(not p.exists() and not p.is_symlink() for p in [packet,work,supervisor,launcher_work]),'runtime namespace appeared during admission wait')
        hash_plan=d.inherit(entry.HASH_SOURCE)
        d.add(entry.HASH_SOURCE/'snapshot-plan.json',snapshot=True)
        # Exact published identities of three completed hash-owner rows omitted
        # by the historical inputs table; no guessed current identities.
        adapter_binding=modules.collector.read(d.add(STARTUP_SOURCE/'source-bindings.json',snapshot=True))
        closure=adapter_binding['reader_closure']
        for ref in [closure['source'],closure['census']]:d.add(ref['path'],ref,snapshot=True)
        for name,row in closure['files'].items():d.add(name,row,snapshot=True)
        d.tree(works['hash'])
        # The completed hash independent audit covers its outer/launcher, and
        # both raw owner histories are frozen explicitly for later readback.
        hash_outer=ROOT/'.work/experiments/hir-options-hash-driver-supervisor-02'
        hash_dispatcher=ROOT/'.work/hash-driver-launch-execution-02'
        d.tree(hash_outer);d.tree(hash_dispatcher)
        for role,ref in audits.items():d.add(ref['path'],ref,snapshot=True)
        for path,row in checked_sources.items():d.add(path,row,snapshot=True)
        predecessor=modules.collector.read(d.add(HERE/'source-bindings.json',snapshot=True))
        for path,row in predecessor['predecessor_sources'].items():d.add(path,row,snapshot=True)
        def read_json(path):return modules.collector.read(d.add(path))
        def read_bytes(path):return d.add(path).read_bytes()
        def sha(path):return d.files[str(d.add(path))]['sha256']
        terminal=read_json(works['hash']/'receipt.json');outer=read_json(hash_outer/'status.json')
        dispatch=read_json(hash_dispatcher/'record.json');hash_launch=read_json(entry.HASH_SOURCE/'launch.json')
        f.require(outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid']
            and outer['supervisor_pid']==terminal['parent_pid'] and outer['command']==hash_launch['command'][6:]
            and outer['cwd']==str(ROOT) and outer['plan_sha256']==sha(hash_outer/'plan.json')
            and outer['log_sha256']==sha(hash_outer/'command.log')
            and outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=terminal['finished_at']<=outer['finished_at'],
            'actual hash supervisor association differs')
        f.require(dispatch['status']=='terminal-observed' and dispatch['returncode']==dispatch['launcher_returncode']==0
            and dispatch['started_at']<=dispatch['launcher_finished_at']<=dispatch['finished_at']
            and outer['finished_at']<=dispatch['terminal_observed_at']<=dispatch['finished_at']
            and dispatch['outer_sha256']==sha(hash_outer/'status.json') and dispatch['command']==hash_launch['command']
            and dispatch['cwd']==str(ROOT) and dispatch['environment']==hash_launch['environment']
            and dispatch['launch_path']==str(entry.HASH_SOURCE/'launch.json')
            and dispatch['launch_sha256']==sha(entry.HASH_SOURCE/'launch.json')
            and hash_launch['inputs_sha256']==sha(entry.HASH_SOURCE/'inputs.json')==terminal['inputs_sha256']
            and hash_launch['plan_sha256']==sha(entry.HASH_SOURCE/'plan.json')
            and Path(dispatch['launcher_source_path'])==entry.HASH_SOURCE/'launch.py'
            and sha(dispatch['launcher_source_path'])==dispatch['launcher_source_sha256'],
            'actual hash dispatcher/launch/source association differs')
        for stream in ['stdout','stderr']:
            f.require(sha(hash_dispatcher/stream)==dispatch[stream+'_sha256'],'actual hash dispatcher raw differs')
        handoff=read_json(hash_dispatcher/'stdout')
        f.require(dispatch['supervisor_handoff']==handoff and handoff['supervisor_pid']==outer['supervisor_pid']
            and handoff['directory']==str(hash_outer) and dispatch['outer_status']==outer['status']
            and dispatch['supervisor_pid']==outer['supervisor_pid'] and dispatch['controller_pid']==terminal['pid'],
            'actual hash dispatcher handoff differs')
        hash_launcher=dict(path=str(hash_dispatcher/'record.json'),sha256=sha(hash_dispatcher/'record.json'),
            source=dict(path=dispatch['launcher_source_path'],sha256=dispatch['launcher_source_sha256']),
            outer=dict(path=str(hash_outer/'status.json'),sha256=sha(hash_outer/'status.json')))
        for path in [hash_dispatcher/'record.json',entry.HASH_SOURCE/'launch.json',Path(dispatch['launcher_source_path'])]:d.add(path,snapshot=True)
        for name,resolved in hash_plan['executor_routes'].items():
            f.require(str(Path(name).resolve(strict=True))==resolved,'inherited executor route differs');d.routes[name]=resolved
        for name in [Path(sys.executable),Path('/opt/homebrew/bin/python3'),Path('/usr/bin/otool'),Path('/usr/bin/xcrun')]:
            resolved=name.resolve(strict=True);d.add(resolved);d.routes[str(name)]=str(resolved)
            if name.is_symlink():d.link(name)
        control=read_json(CONTROL_WORK/'receipt.json');audit=read_json(CONTROL_AUDIT);tested=read_json(CONTROLS/'inputs.json')
        f.require(control['status']=='passed' and control['controls_passed']==21 and audit['status']=='verified'
            and audit['receipt_sha256']==sha(CONTROL_WORK/'receipt.json')
            and control['inputs_sha256']==sha(CONTROLS/'inputs.json'),'actual21 runtime-adapter control proof required')
        for name,row in tested['files'].items():d.add(name,row,snapshot=True)
        d.tree(CONTROL_WORK);d.tree(O/'.work/experiments/runtime-adapter-controls-supervisor-01')
        d.add(CONTROL_AUDIT,snapshot=True);d.add(CONTROLS/'launch.json',snapshot=True)
        for path in [entry.CATALOG_SOURCE,entry.CATALOG_TEST,entry.CATALOG_CONTROLS/'inputs.json',
                     entry.CATALOG_CONTROLS/'launch.json',entry.CATALOG_AUDIT]:d.add(path,snapshot=True)
        catalog_tested=read_json(entry.CATALOG_CONTROLS/'inputs.json')
        for name,row in catalog_tested['files'].items():d.add(name,row,snapshot=True)
        d.tree(entry.CATALOG_WORK)
        for path in [HERE/'prerequisites.py',HERE/'test_prerequisite_successor.py',entry.RUNTIME_CONTROLS/'inputs.json',
                     entry.RUNTIME_CONTROLS/'launch.json',entry.RUNTIME_CONTROL_AUDIT]:d.add(path,snapshot=True)
        runtime_tested=read_json(entry.RUNTIME_CONTROLS/'inputs.json')
        for name,row in runtime_tested['files'].items():d.add(name,row,snapshot=True)
        d.tree(entry.RUNTIME_CONTROL_WORK)
        c=modules.copies
        for path in [c.PROPOSAL,c.SOURCE/'references.py',c.SOURCE/'test_references.py',
                     c.CONTROLS/'inputs.json',c.CONTROLS/'launch.json',c.CONTROL_AUDIT]:d.add(path,snapshot=True)
        for name,row in read_json(c.CONTROLS/'inputs.json')['files'].items():d.add(name,row,snapshot=True)
        d.tree(c.CONTROL_WORK)
        source_manifest=dict(path=str(args['startup_source_manifest']),sha256=args['startup_source_manifest_sha256'])
        d.add(source_manifest['path'],source_manifest,snapshot=True)
        source_rows=read_json(source_manifest['path'])
        f.require(set(source_rows)=={'status','files'}
            and source_rows['status']=='reviewed-runtime-installation05-startup-source-closure'
            and ({str(ADAPTER/name) for name in entry.RETRY_SOURCE_NAMES}
                 | {str(STARTUP_SOURCE/name) for name in STARTUP_FILES})<=set(source_rows['files']),
            'complete reviewed startup source closure required')
        for name,row in source_rows['files'].items():
            f.require(set(row)=={'sha256','size','identity'}
                and (name not in d.files or d.files[name]==row),'unequal startup source overlap')
            d.add(name,row,snapshot=True)
        f.require({p.name for p in STARTUP_SOURCE.iterdir()}==STARTUP_FILES,'exact qualified startup source membership required')
        for name in sorted(STARTUP_FILES):d.add(STARTUP_SOURCE/name,snapshot=True)
        for name in entry.RETRY_SOURCE_NAMES:d.add(entry.PREFLIGHT_SOURCE/name,snapshot=True)
        for name in entry.INSTALLATION_SOURCE_NAMES:d.add(ADAPTER/name,snapshot=True)
        for path in [entry.RETRY_CONTROLS/'inputs.json',entry.RETRY_CONTROLS/'launch.json',entry.RETRY_CONTROL_AUDIT]:
            d.add(path,snapshot=True)
        f.require(sha(entry.RETRY_CONTROL_AUDIT)==args['retry_audit_sha256'],'exact separately reviewed retry audit required')
        for name,row in read_json(entry.RETRY_CONTROLS/'inputs.json')['files'].items():d.add(name,row,snapshot=True)
        d.tree(entry.RETRY_CONTROL_WORK)
        for path in [entry.INSTALLATION_CONTROLS/'inputs.json',entry.INSTALLATION_CONTROLS/'launch.json',entry.INSTALLATION_CONTROL_AUDIT]:d.add(path,snapshot=True)
        f.require(sha(entry.INSTALLATION_CONTROL_AUDIT)==args['installation_audit_sha256'],'exact separately reviewed installation audit required')
        for name,row in read_json(entry.INSTALLATION_CONTROLS/'inputs.json')['files'].items():d.add(name,row,snapshot=True)
        d.tree(entry.INSTALLATION_CONTROL_WORK)
        for path in [STARTUP_CONTROLS/'inputs.json',STARTUP_CONTROLS/'launch.json',STARTUP_AUDIT]:d.add(path,snapshot=True)
        f.require(sha(STARTUP_AUDIT)==args['startup_audit_sha256'],'exact separately reviewed startup controls audit required')
        for name,row in read_json(STARTUP_CONTROLS/'inputs.json')['files'].items():d.add(name,row,snapshot=True)
        d.tree(STARTUP_WORK)
        # The Reader's complete union extends its immutable original; no live
        # environment is changed to mimic a historical launch.
        d.imports()
        combined=dict(files=d.files,links=d.links,absent_paths=sorted(d.absent),executor_routes=d.routes)
        census=read_json(closure['census']['path'])
        f.require(set(census['required_paths'])<=set(combined['files']),'complete qualified Reader physical dependency closure required')
        partition=lambda r:entry.copy_partition(modules,r,load=factory.load,directory_record=f.ordinary_directory)
        reader=modules.prerequisites.Reader(modules.stage,modules.hash_modules,combined_freeze=combined,references=audits,
            read_json=read_json,sha=sha,copy_partition=partition)
        retirement=entry.retirement_qualification(modules,
            dict(path=str(args['copy_retirement_audit']),sha256=args['copy_retirement_audit_sha256']),
            reader.copy_state,read_json=read_json,sha=sha)
        for name in reader.copy_state['historical_files']:d.absent.add(name)
        qualification=reader.check(full=True)
        runtime_qualification=entry.runtime_qualification(reader)
        catalog_qualification=entry.catalog_qualification(reader)
        startup_qualification=entry.controls_qualification(reader,source=STARTUP_SOURCE/'environment.py',
            test=STARTUP_SOURCE/'test_environment.py',controls=STARTUP_CONTROLS,work=STARTUP_WORK,
            audit_path=STARTUP_AUDIT,count=STARTUP_CONTROL_COUNT,
            additional_sources=[STARTUP_SOURCE/'audit_owner.py'],additional_tests=[STARTUP_SOURCE/'test_audit_owner.py'])
        f.require(startup_qualification['audit']['sha256']==args['startup_audit_sha256'],
            'startup qualification changed')
        installation_qualification=entry.installation_qualification(reader)
        f.require(installation_qualification['audit']['sha256']==args['installation_audit_sha256'],'installation qualification changed')
        retry_qualification=entry.retry_qualification(reader)
        f.require(retry_qualification['audit']['sha256']==args['retry_audit_sha256'],'retry qualification changed')
        startup=factory.load('startup_environment',STARTUP_SOURCE/'environment.py',reader.reader.frozen)
        catalog=factory.load('completed_catalog',entry.CATALOG_SOURCE,lambda p:d.add(p,snapshot=True))
        compiled=read_json(COMPILED);provider=read_json(PROVIDER);remap=read_json(REMAP);old_spec=read_json(OLD_SPEC);old_policy=read_json(OLD_POLICY)
        source=Path(hash_plan['metadata_plan']['source']);sysroot=Path(hash_plan['roles']['runtime_compiler'])
        f.require(source==modules.hash_modules['core'].S and sysroot==modules.hash_modules['core'].E2,'actual compiler output roots differ')
        policy=modules.discovery.source_policy(modules.q,compiled,remap,old_policy,read_json=read_json,read_bytes=read_bytes,sha=sha,source=source)
        provider_ref=dict(path=str(PROVIDER),sha256=sha(PROVIDER))
        candidate=modules.discovery.candidate(modules.q,qualification,compiled,old_spec,provider,provider_ref,policy,
            source=source,sysroot=sysroot,read_json=read_json,read_bytes=read_bytes,sha=sha)
        for component in candidate['components']:
            d.tree(component['root'])
            for name,row in component['files'].items():d.add(Path(component['root'])/name,row)
        environment=dict(hash_plan['environment']);environment['TMPDIR']=str(work/'tmp')
        modules.q.std.validate_environment(environment)
        preflight=None
        if phase=='installation':
            f.require(args['source_preflight_audit'] is not None and args['source_preflight_audit_sha256'] is not None,'actual independent source-preflight audit required')
            prior=entry.preflight_routes(read_json=read_json,sha=sha)
            previous=Path(prior['packet']);previous_work=Path(prior['work'])
            d.inherit(previous);d.tree(previous);d.tree(previous_work)
            for key in ['supervisor','launcher_execution','preparation_execution']:d.tree(Path(prior[key]))
            history=factory.load('preflight_history',HERE/'preflight_history.py',lambda p:d.add(p,snapshot=True))
            preflight=entry.completed_preflight(modules,candidate=candidate,
                audit_reference=dict(path=str(args['source_preflight_audit']),sha256=args['source_preflight_audit_sha256']),
                read_json=read_json,read_bytes=read_bytes,sha=sha)
        startup_observations['before_packet']=dict(os.environ)
        startup_derivation=startup.derive(environment,
            startup.decode(args['preparation_passed_environment_json']),startup_observations,
            platform=sys.platform,uid=os.getuid())
        launch_environment=startup.validate(environment,startup_derivation)
        modules.q.std.validate_environment(launch_environment)
        startup_environment=dict(derivation=startup_derivation,
            policy=dict(path=str(STARTUP_SOURCE/'environment.py'),sha256=sha(STARTUP_SOURCE/'environment.py')),
            qualification=startup_qualification,
            preparer=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__).resolve())),
            preparation_record=str(preparation_record),source_manifest=source_manifest)
        packet.mkdir()
        policy_path=packet/'source-policy-proof.json';write(policy_path,policy);d.add(policy_path,snapshot=True)
        if phase=='installation':
            spec=modules.recipe.final_specification(modules.q,candidate,preflight_reference=preflight['reference'],preflight=preflight['result'],
                policy_reference=dict(path=str(policy_path),sha256=sha(policy_path)),policy=policy)
        else:spec=candidate
        specification=packet/'specification.json';write(specification,spec);d.add(specification,snapshot=True)
        if phase=='preflight':
            children=modules.recipe.preflight_commands(modules.q,spec,R,work/'source-probe',environment);key=modules.q.runtime.digest(modules.q.runtime.identity_for(spec));installation=None
        else:
            key,new_sysroot,children=modules.recipe.installation_commands(modules.q,spec,R,work,environment);installation=new_sysroot.parent
            f.require(not installation.exists() and not installation.is_symlink(),'new runtime prefix must be absent')
        monitor=modules.controller.configure_monitor(modules.monitor,installation_directory=installation)
        # Both outputs are future roots at preparation, so declare the launcher
        # explicitly rather than allowing its creation to invalidate the budget.
        roots={work,launcher_work}
        failed=routes['failed_predecessor']
        failed_review_reference=dict(path=str(ROOT/'results/runtime04-preflight-capacity-failure-01/review.json'),
            sha256='3d29955a0512ba66dd86da9f50c18c93a013cbb0e648f5a25ae378eaaf1afaa3')
        d.add(failed_review_reference['path'],failed_review_reference,snapshot=True)
        failed_review=read_json(failed_review_reference['path'])
        f.require(failed_review['status']=='closed-capacity-failure-before-compiler-probes'
            and failed_review['qualification_passed'] is False
            and failed_review['actual_compiler_children']==0 and failed_review['source_probe_directory_absent'] is True,
            'exact published failed predecessor review required')
        for row in failed_review['packet_references'].values():
            d.add(row['path'],dict(sha256=row['sha256'],size=row['bytes']),snapshot=True)
        for row in failed_review['retained_records'].values():
            d.add(row['original_path'],dict(sha256=row['sha256'],size=row['bytes']),snapshot=True)
        failed_probe=Path(failed['work'])/'source-probe'
        f.require(not failed_probe.exists() and not failed_probe.is_symlink(),'failed04 probe absence changed')
        d.absent.add(str(failed_probe))
        for name in ['packet','work','supervisor','launcher_execution']:d.tree(Path(failed[name]))
        previous_packet=Path(failed['packet']);previous_work=Path(failed['work'])
        previous_outer=Path(failed['supervisor']);previous_launcher=Path(failed['launcher_execution'])
        failed_terminal=read_json(previous_work/'receipt.json');failed_outer=read_json(previous_outer/'status.json')
        failed_launch=read_json(previous_packet/'launch.json');failed_dispatch=read_json(previous_launcher/'record.json')
        f.require(failed_terminal['status']=='failed' and failed_terminal['phase']=='preflight'
            and failed_terminal['children']==[] and 'admitted_at' not in failed_terminal
            and 'source_snapshots_sha256' not in failed_terminal
            and failed_terminal['error']=="RuntimeError('insufficient free space: 23099760640')",
            'exact closed pre-admission failure history required')
        f.require(failed_outer['status']=='finished' and type(failed_outer['returncode']) is int and failed_outer['returncode']==1
            and failed_outer['child_pid']==failed_terminal['pid'] and failed_outer['supervisor_pid']==failed_terminal['parent_pid']
            and failed_outer['command']==failed_launch['command'][6:] and failed_outer['cwd']==str(R)
            and failed_outer['plan_sha256']==sha(previous_outer/'plan.json')
            and failed_outer['log_sha256']==sha(previous_outer/'command.log'), 'failed predecessor supervisor differs')
        f.require(failed_dispatch['status']=='terminal-observed' and failed_dispatch['returncode']==1
            and failed_dispatch['launcher_returncode']==0 and failed_dispatch['outer_sha256']==sha(previous_outer/'status.json')
            and failed_dispatch['launch_sha256']==sha(previous_packet/'launch.json')
            and failed_dispatch['command']==failed_launch['command'] and failed_dispatch['cwd']==str(R)
            and failed_dispatch['controller_pid']==failed_terminal['pid']
            and failed_dispatch['supervisor_pid']==failed_terminal['parent_pid']
            and failed_dispatch['environment']==failed_launch['environment']
            and failed_outer['child_started_at']<=failed_terminal['started_at']<=failed_terminal['finished_at']
                <=failed_outer['finished_at']<=failed_dispatch['terminal_observed_at']<=failed_dispatch['finished_at'],
            'failed predecessor launcher/chronology differs')
        for stream in ['stdout','stderr']:
            f.require(sha(previous_launcher/stream)==failed_dispatch[stream+'_sha256'],'failed launcher raw differs')
        failed_reference=dict(receipt=dict(path=str(previous_work/'receipt.json'),sha256=sha(previous_work/'receipt.json')),
            outer=dict(path=str(previous_outer/'status.json'),sha256=sha(previous_outer/'status.json')),
            launcher=dict(path=str(previous_launcher/'record.json'),sha256=sha(previous_launcher/'record.json')),
            phase='preflight',status='failed-before-admission',children=0,review=failed_review_reference)

        for owner in monitor.EVIDENCE_OWNERS:
            for path in (owner/'.work').iterdir():
                if path.name.startswith(monitor.EVIDENCE_PREFIXES) and (path.is_dir() or path.is_symlink()):
                    f.require(path.is_dir() and not path.is_symlink(),'indirect candidate evidence root');roots.add(path)
        monitor.evidence_contract(work,sorted(roots))
        plan=dict(status='prepared-unrun',phase=phase,owner=str(R),work=str(work),supervisor_work=str(supervisor),hash_source=str(entry.HASH_SOURCE),
            independent_audits=audits,qualified_prerequisites=qualification,hash_launcher=hash_launcher,specification=dict(path=str(specification),sha256=sha(specification)),
            source_policy=dict(path=str(policy_path),sha256=sha(policy_path)),provider_comparison=provider_ref,
            adapter_controls=dict(receipt=str(CONTROL_WORK/'receipt.json'),audit=str(CONTROL_AUDIT)),runtime_key=key,
            catalog_qualification=catalog_qualification,
            runtime_adapter_qualification=runtime_qualification,retry_qualification=retry_qualification,installation_qualification=installation_qualification,
            attempt=dict(path=str(entry.ROUTES),sha256=entry.ROUTES_SHA256),failed_predecessor=failed_reference,
            copy_retirement=retirement,
            environment=environment,launch_environment=launch_environment,children=children,evidence_roots=sorted(map(str,roots)),
            startup_environment=startup_environment,
            capacity=routes['capacity'])
        if phase=='installation':plan.update(sysroot=str(new_sysroot),source_preflight=preflight['reference'],source_preflight_readback=preflight)
        for path in HERE.iterdir():
            if path.is_file():d.add(path,snapshot=True)
        d.add(R/'scripts/supervise_experiment.py',snapshot=True)
        reader.reader.snapshot_qualification()
        snapshots=factory.load('qualified_snapshots',modules.stage.SNAPSHOT_SOURCE,lambda p:d.add(p,snapshot=True))
        def file_record(path):
            path=d.add(path)
            return dict(path=str(path),**d.files[str(path)])
        plan['snapshot_reuse']=entry.completed_catalog(modules,reader,catalog,snapshots,plan['evidence_roots'],
            read_json=read_json,read_bytes=read_bytes,sha=sha,file_record=file_record,directory_record=f.ordinary_directory,guard=d.floor,
            preflight_owner=entry.preflight_catalog_owner(modules,plan,read_json=read_json,read_bytes=read_bytes,sha=sha))
        d.imports()
        write(packet/'plan.json',plan);d.add(packet/'plan.json',snapshot=True)
        freeze=dict(files=d.files,links=d.links,absent_paths=sorted(d.absent),executor_routes=d.routes,python=str(Path(sys.executable).resolve(strict=True)),
            historical_copies=reader.copy_state['references'],
            plan_sha256=sha(packet/'plan.json'),launch_environment=launch_environment,snapshot_inputs=sorted(d.snapshots))
        table=modules.stage.load_file_table(freeze,modules.hash_modules['comp'])
        wire=table.split(freeze,base_path=entry.FILE_TABLE_BASE['path'],base_sha256=entry.FILE_TABLE_BASE['sha256'],guard=d.floor)
        f.require(table.encoded(modules.stage.expand_file_table(wire,table,guard=d.floor))==table.encoded(freeze),'complete runtime table roundtrip differs')
        write(packet/'inputs.json',wire);inputs_sha=f.digest(packet/'inputs.json')
        rows=entry.records(freeze,packet,inputs_sha,f);selected=catalog.select(rows,plan['snapshot_reuse'])
        projection=snapshots.measure(rows,entry.LIMITS,d.floor,reuse=selected['records'],evidence_roots=selected['evidence_roots'])
        budget=monitor.sample(evidence_root=work,evidence_roots=sorted(roots));amount=entry.reservation(projection,rows,catalog)
        f.require(monitor.rejection(budget) is None and budget['evidence_allocated_bytes']+amount<=256*2**20,'combined runtime proof/evidence reservation unavailable')
        projection_plan=dict(inputs_sha256=inputs_sha,helper=dict(path=str(modules.stage.SNAPSHOT_SOURCE),sha256=sha(modules.stage.SNAPSHOT_SOURCE)),
            limits=entry.LIMITS,projection=projection,remaining_evidence_reservation_bytes=entry.REMAINING_RESERVATION,
            reuse_selection=selected,
            measured_existing_evidence_bytes=budget['evidence_allocated_bytes'],projected_reservation_bytes=amount,evidence_cap_bytes=256*2**20)
        projection_bytes=snapshots.encoded(projection_plan);f.require(len(projection_bytes)<=entry.LIMITS['maximum_manifest_bytes'],'projection manifest bound')
        with (packet/'snapshot-plan.json').open('xb') as stream:stream.write(projection_bytes);stream.flush();os.fsync(stream.fileno())
        # Full prepared readback remains read-only; no Controller constructor,
        # execute, source probe, copy, or final validator invocation occurs.
        final=f.Frozen(packet/'inputs.json',inputs_sha,output_root=work,table=table,base=entry.FILE_TABLE_BASE);final.check(True)
        modules.prerequisites.Reader(modules.stage,modules.hash_modules,combined_freeze=freeze,references=audits,
            read_json=final.read_json,sha=final.sha,
            copy_partition=lambda r:entry.copy_partition(modules,r,load=factory.load,directory_record=f.ordinary_directory,
                saved=freeze['historical_copies'])).check(full=True)
        f.require(dict(os.environ)==startup_observations['before_packet'],'preparer environment changed after packet encoding')
        write(packet/'metadata-preflight.json',dict(status='passed-read-only-discovery',phase=phase,started_at=started,finished_at=time.time(),
            free_bytes_before=free_before,free_bytes_after=d.owned.disk(R,9),files=len(d.files),bytes=d.total,work_created=False,children=0,inputs_sha256=inputs_sha,
            startup_environment=startup_environment,environment_at_completion=dict(os.environ)))
        launch=dict(status='prepared-unrun-awaiting-exact-review',cwd=str(R),environment=launch_environment,command=[freeze['python'],'-B',str(R/'scripts/supervise_experiment.py'),
            '--run-id',supervisor.name,'--',freeze['python'],'-B',str(ADAPTER/'entry.py'),'--packet',str(packet),
            '--inputs-sha256',inputs_sha,'--snapshot-plan-sha256',f.digest(packet/'snapshot-plan.json')],inputs_sha256=inputs_sha,
            snapshot_plan_sha256=f.digest(packet/'snapshot-plan.json'),plan_sha256=sha(packet/'plan.json'),helper_sha256=sha(ADAPTER/'entry.py'),children=len(children),capacity=plan['capacity'])
        write(packet/'launch.json',launch)
        print(json.dumps(dict(status='prepared-unrun',phase=phase,launch_sha256=f.digest(packet/'launch.json'),inputs_sha256=inputs_sha,files=len(d.files),bytes=d.total),indent=2))


if __name__=='__main__':main()

"""Independent retained-data audit. No workload/controller imports or execution."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path('/Users/danluu/dev/rust-interp-perf-20260912')
B = ROOT / '.work/build-general-20260912'
R = B / 'local-export-adoption-recovery-01'
PROOFS = {}

def digest(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()

def bind(path, expected=None):
    path = Path(path)
    actual = digest(path)
    assert expected is None or actual == expected, ('hash', str(path), expected, actual)
    old = PROOFS.setdefault(str(path), actual)
    assert old == actual, ('changed during audit', str(path))
    return actual

def read(path):
    bind(path)
    return json.loads(Path(path).read_text())

def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), (a, b)

def cpu(c):
    for k in ['user_seconds', 'system_seconds', 'total_seconds']:
        assert type(c[k]) in (float, int) and math.isfinite(c[k]) and c[k] >= 0, (k,c)
    close(c['user_seconds'] + c['system_seconds'], c['total_seconds'])

frozen = read(B / 'local-export-adoption-frozen.json')
commands = read(B / 'local-export-adoption-commands.json')
recovery = read(R / 'recovery.json')
controller = read(R / 'screen-controller.json')
old = read(B / 'local-export-adoption-screen-controller.json')
unstarted = read(R / 'unstarted-evidence.json')
assessment = read(R / 'screen-assessment.json')
for mapping in [frozen['proofs'], frozen['source_proofs'], recovery['files'], controller['recovery_proofs'], assessment['proofs']]:
    for path, expected in mapping.items():
        if path in PROOFS:
            assert PROOFS[path] == expected, ('conflicting proof', path)
        else:
            bind(path, expected)
print('All named frozen/recovery/assessment proof hashes checked:', len(PROOFS), flush=True)

assert digest(B / 'local-export-adoption-frozen.json') == recovery['original_frozen_sha256'] == controller['frozen_sha256']
assert digest(B / 'local-export-adoption-screen-controller.json') == recovery['original_stopped_controller_sha256']
assert old['status'] == 'stopped' and old['calls'] == old['admissions'] == []
assert old['error'].rstrip().endswith('RuntimeError: admission lock unavailable; no workload launched')
assert old['planned_commands'] == frozen['commands']['screen']
assert unstarted['calls'] == unstarted['admissions'] == []
assert old['finished_at'] < unstarted['recorded_at'] < controller['started_at']
assert controller['recovery_manifest_sha256'] == digest(R / 'recovery.json')
assert recovery['workload_commands_changed'] is False
assert controller['admission_wait_seconds'] == recovery['admission_wait_seconds'] == 3600
assert controller['recovery_proofs'] == {**recovery['files'], str(R / 'recovery.json'): digest(R / 'recovery.json')}
expected_absent = [str(path) for c in frozen['cases'] for path in [ROOT/'.work/runs'/c['run_id'], ROOT/'results'/c['run_id'], *map(Path,c['cache_workspaces'].values())]]
assert len(expected_absent) == len(set(expected_absent)) == 32
assert recovery['absent_workload_paths'] == unstarted['absent_workload_paths'] == expected_absent
for phase in ['screen', 'confirmation']:
    planned = [{**x, 'command': [frozen['executables']['python'], *x['command'][1:]]} for x in commands[phase]]
    assert frozen['commands'][phase] == planned
assert controller['status'] == 'complete' and controller['phase'] == 'screen' and controller['cwd'] == str(ROOT)
assert controller['planned_commands'] == frozen['commands']['screen']
assert len(controller['calls']) == 12 and len(controller['admissions']) == 6
previous = controller['started_at']
for c, p in zip(controller['calls'], frozen['commands']['screen']):
    assert {k:c[k] for k in ['label','kind','command']} == p
    assert c['status'] == 'complete' and c['returncode'] == 0
    assert previous <= c['started_at'] <= c['finished_at']
    previous = c['finished_at']
    bind(R/(c['label']+'-controller.log'), c['log_sha256'])
assert previous <= controller['finished_at']
cases = [c for c in frozen['cases'] if c['phase'] == 'screen']
for a, c, call in zip(controller['admissions'], cases, controller['calls'][::2]):
    assert a['label'] == c['run_id'] == call['label']
    assert a['minimum_gib'] == c['minimum_admission_gib'] and a['free_bytes'] >= a['minimum_gib']*2**30
    assert a['lock_wait_started'] <= a['time'] <= call['started_at'] <= a['lock_released_at'] <= call['finished_at']
assert len({tuple(a['lock_identity']) for a in controller['admissions']}) == 1
assert (ROOT/'.work/benchmark.lock').resolve() == Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')

# Reproduce the installer key from each source snapshot, preserving manifest order.
source_details = {}
for mode, bundle in frozen['bundles'].items():
    snap = Path(bundle['source_snapshot'])
    src = read(snap/'source.json')
    h = hashlib.sha256()
    for relative, expected in src['files'].items():
        bind(snap/relative, expected)
        if mode == 'candidate':
            bind(ROOT/relative, expected)
        h.update(relative.encode()+b'\0'+(snap/relative).read_bytes())
    assert h.hexdigest() == src['tool_key'] == bundle['tool_key']
    for name, expected in bundle['binaries'].items():
        bind(Path(bundle['directory'])/name, expected)
    source_details[mode] = {'inputs':len(src['files']), 'key':h.hexdigest(), 'binaries':bundle['binaries'], 'built_vm_recorded_separately':bundle['built_binaries']['rust-interp-vm']['sha256']}
assert source_details['candidate']['inputs'] == 146
assert source_details['baseline']['inputs'] == 137
assert source_details['baseline']['binaries']['rust-interp-vm'] == source_details['candidate']['binaries']['rust-interp-vm']

histories = []
all_pairs = []
artifact_bindings = []
total_primary = total_checks = 0
flags = '-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240'
for case in cases:
    run = case['run_id']
    raw = ROOT/'.work/runs'/run
    report = read(ROOT/'results'/run/'summary.json')
    verify = read(ROOT/'results'/run/'verification.json')
    records = read(raw/'records.json')
    checks = read(raw/'check-records.json')
    transitions = read(raw/'source-transitions.json')
    active = read(raw/'active-command.json')
    history_call = next(c for c in controller['calls'] if c['label']==run)
    assert active['status']=='finished' and active['returncode']==0
    assert active['mode']=='check-floor' and active['state']==-2 and active['cycle']==1
    assert active['parent_pid']==history_call['child_pid']
    assert history_call['started_at'] <= active['started_at'] <= active['finished_at'] <= history_call['finished_at']
    assert len(records) == case['primary_commands'] == 24
    assert len(checks) == case['check_commands'] == 8
    total_primary += len(records); total_checks += len(checks)
    assert report['samples'] == [{k:v for k,v in r.items() if k != 'calls'} for r in records]
    assert report['source_transitions'] == transitions
    assert report['check_floor']['samples'] == [{k:v for k,v in c.items() if k not in ['command','stdout','stderr']} for c in checks]
    for k in ['project','revision','workflow','cycles','tests','initial_mode_order','case_sha256']:
        assert report[k] == case[k], (run,k)
    assert report['test_source_unchanged'] is True and report['wrong_production_edit_rejected'] is True
    assert report['cache_workspaces'] == case['cache_workspaces']
    assert report['cache_namespaces'] == {m:run+':'+m for m in ['baseline','candidate']}
    assert report['native_control'] == {'profile':'repository','jobs':18,'test_threads':'1','rustflags':[],'isolation':'ordinary libtest batch'}
    assert report['std_mir']['key'] == frozen['std_mir_key'] and report['std_mir']['metadata_bytes'] == 112958025
    for k,v in dict(batch=True,compare_isolated_batches=False,cargo_timings=False,vary_selection=False,build_tool_opt_level=0,build_jobs=18,custom_build_jobs={'baseline':18,'candidate':18},instruction_limit=100000000000,allocation_limit=150000,inline_leaves=True,baseline_inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True,guest_mir_opt_level=3,guest_mir_inline_scale=8,minimum_free_gib=1,baseline_guest_mir_opt_level=None).items():
        assert report[k] == v, (run,k)
    assert report['build_metrics']['boundary'] == 'launcher start to validated artifact ready, before VM invocation'
    for path, expected in report['scripts_sha256'].items(): bind(ROOT/path, expected)
    for k in ['measurement_controls_verified','explicit_controls_verified','paired_bytecode_identical','build_to_ready_metrics_verified','restored_original_build_and_execution_verified']:
        assert verify[k] is True
    assert verify['commands']==24 and verify['edited_pairs']==5 and verify['check_commands']==8 and verify['exact_artifact_hashes_verified']==16
    assert report['restored_original'] == {'verified':True,'source_sha256':case['original_source_sha256'],'cycle':1,'state':-2,'commands':3,'excluded_from_edited_medians':True}
    state_sequence = [0,-1,1,2,3,4,5,-2]
    assert [t['state'] for t in transitions] == state_sequence
    assert [r['state'] for r in records] == [s for s in state_sequence for _ in range(3)]
    assert [c['state'] for c in checks] == state_sequence
    expected_source = {int(k):v for k,v in case['source_states'].items()}; expected_source[-2]=case['original_source_sha256']
    for t, order in zip(transitions,report['mode_orders']):
        assert t['source_sha256'] == expected_source[t['state']]
        assert [r['mode'] for r in records if r['state']==t['state']] == order['modes']
    launches={}
    for row in records:
        assert row['tests'] == case['tests'] and row['source_sha256']==expected_source[row['state']]
        assert len(row['calls']) == 1
        call = row['calls'][0]
        cpu(call['cpu']); close(call['cpu']['total_seconds'],row['cpu_seconds'])
        assert not any(x in call['stderr'] for x in ['rust-interp-function-costs: ','rust-interp-export-timings: '])
        mode = row['mode']; state = row['state']
        expected_returncode = (101 if mode=='native' else 1) if state == -1 else 0
        assert call['returncode'] == expected_returncode
        assert re.search(r'^\s*(?:Checking|Compiling) '+re.escape(case['package'])+r' v',call['stderr'],re.M), (run,state,mode,'fresh compile')
        assert 'Finished `test` profile' in call['stderr']
        argv = call['command']
        if mode == 'native':
            assert row['artifacts']==[] and call['rustflags'] is None
            expected=['cargo','+nightly-2026-09-08','test','--manifest-path',str(ROOT/'.work/sources'/case['project']/'Cargo.toml'),'--package',case['package'],'--lib','--locked','--offline','--jobs','18','--target-dir',str(raw/'native'),'--','--exact','--test-threads=1',*case['tests']]
            assert argv == expected, (run,state,'native argv')
            if state==-1: assert 'test result: FAILED.' in call['stdout'] and 'assertion' in call['stdout']
            else: assert f'test result: ok. {len(case["tests"])} passed; 0 failed;' in call['stdout']
            continue
        bundle=frozen['bundles'][mode]
        tool=report['tool_builds'][mode]
        assert tool['tool_key']==bundle['tool_key'] and tool['vm_sha256']==bundle['binaries']['rust-interp-vm'] and tool['exporter_sha256']==bundle['binaries']['rust-interp-mir-export']
        expected=[str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(ROOT/'.work/sources'/case['project']/'Cargo.toml'),'--package',case['package'],'--jobs','18','--test-body','--engine','jit','--instruction-limit','100000000000','--cache-namespace',run+':'+mode,'--tool-key',bundle['tool_key'],'--allocation-limit','150000','--inline-leaves','--jit-resumable-calls','--jit-persistent-registers','--trap-unsupported-calls','--run-try-callbacks','--std-mir']
        for entry in case['tests']: expected += ['--entry',entry]
        assert argv[1:] == expected and str(Path(argv[0]).resolve()) == frozen['executables']['python']
        assert call['rustflags']==flags and call['encoded_rustflags'] is None
        messages=[json.loads(line[len('rust-interp-launch: '):]) for line in call['stderr'].splitlines() if line.startswith('rust-interp-launch: ')]
        assert len(messages)==1 and messages[0]==call['launch']
        launch=messages[0]
        assert launch['tool_key']==bundle['tool_key'] and launch['workspace_path']==case['cache_workspaces'][mode]
        assert launch['compiler_wrapper']['sha256']==bundle['binaries']['rust-interp-rustc-wrapper']
        for k,v in dict(engine='jit',jit_persistent_registers=True,jit_resumable_calls=True,jit_native_calls=False,jit_native_call_stubs=False,inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True,allocation_limit=150000).items(): assert launch[k]==v,(run,k)
        ready=launch['build_to_ready_seconds']; cc=launch['build_to_ready_cpu']
        for c in [cc,cc['self'],cc['children'],launch['cargo_cpu']]:cpu(c)
        for k in ['user_seconds','system_seconds','total_seconds']:
            close(cc[k],cc['self'][k]+cc['children'][k])
            assert launch['cargo_cpu'][k] <= cc['children'][k]+1e-8
            assert cc[k] <= call['cpu'][k]+1e-8
        for k in ['build_to_ready_seconds','execution_seconds','launcher_seconds','cargo_seconds','artifact_hash_seconds']:
            assert math.isfinite(launch[k]) and launch[k]>=0
        assert 0 < launch['cargo_seconds'] <= ready <= launch['launcher_seconds'] <= call['seconds']
        assert abs(launch['launcher_seconds']-ready-launch['execution_seconds']) < 0.01
        close(row['build_to_ready_seconds'],ready); close(row['build_to_ready_cpu_seconds'],cc['total_seconds']);close(row['cargo_cpu_seconds'],launch['cargo_cpu']['total_seconds'])
        assert len(row['artifacts'])==1
        artifact=row['artifacts'][0]; ap=ROOT/artifact['path']
        assert ap.is_relative_to(raw/'artifacts') and ap.stat().st_size==artifact['bytes']==launch['artifact_bytes']
        bind(ap,artifact['sha256']); assert artifact['sha256']==launch['artifact_sha256']
        assert Path(launch['artifact_path']).is_relative_to(Path(case['cache_workspaces'][mode]))
        artifact_bindings.append({'run':run,'cycle':row['cycle'],'state':state,'mode':mode,**artifact})
        if state==-1:
            traps=[s for s in call['stderr'].splitlines() if s.startswith('rust-interp-vm: guest trap: ')]
            test='exhaustive_small_byte_semantics_match_pinned_regex' if case['group']=='token' else 'murmurhash32_inverse_roundtrips'
            assert len(traps)==1 and 'core::panicking::assert_failed' in traps[0] and test in traps[0]
        else: assert call['stdout']=='0\n'
        launches[(state,mode)]=launch
    for check in checks:
        assert check['source_sha256']==expected_source[check['state']] and check['returncode']==0
        cpu(check['cpu']);close(check['cpu_seconds'],check['cpu']['total_seconds'])
        expected=['cargo','+nightly-2026-09-08','check','--manifest-path',str(ROOT/'.work/sources'/case['project']/'Cargo.toml'),'--package',case['package'],'--lib','--locked','--offline','--jobs','18','--target-dir',str(raw/'check'),'--profile','test']
        assert check['command']==expected
        assert re.search(r'^\s*Checking '+re.escape(case['package'])+r' v',check['stderr'],re.M)
    assert active['command']==checks[-1]['command']
    for state in state_sequence:
        assert launches[(state,'baseline')]['artifact_sha256']==launches[(state,'candidate')]['artifact_sha256']
    pairs=[]
    for state in range(1,6):
        baseline,candidate=[launches[(state,m)] for m in ['baseline','candidate']]
        p={'run':run,'group':case['group'],'cycle':0,'state':state,'source_sha256':expected_source[state],'baseline_wall':baseline['build_to_ready_seconds'],'candidate_wall':candidate['build_to_ready_seconds'],'baseline_cpu':baseline['build_to_ready_cpu']['total_seconds'],'candidate_cpu':candidate['build_to_ready_cpu']['total_seconds']}
        p['wall_ratio']=p['candidate_wall']/p['baseline_wall'];p['cpu_ratio']=p['candidate_cpu']/p['baseline_cpu']
        summarized=[x for x in report['comparison']['pairs'] if x['cycle']==0 and x['state']==state]
        assert len(summarized)==1; s=summarized[0]
        assert s['source_sha256']==p['source_sha256'] and s['identical_bytecode'] is True
        for mode in ['baseline','candidate']:
            close(s[mode+'_build_to_ready_seconds'],p[mode+'_wall']);close(s[mode+'_build_to_ready_cpu_seconds'],p[mode+'_cpu'])
        pairs.append(p)
    assert len(report['comparison']['pairs'])==5
    history={'run':run,'group':case['group'],'wall_median':statistics.median(p['wall_ratio'] for p in pairs),'cpu_median':statistics.median(p['cpu_ratio'] for p in pairs)}
    history['guard_pass']=history['wall_median']<=1.05 and history['cpu_median']<=1.05
    histories.append(history);all_pairs.extend(pairs)
    print('Raw history audited:',run,history['wall_median'],history['cpu_median'],flush=True)

assert total_primary==144 and total_checks==48 and len(artifact_bindings)==96 and len(all_pairs)==30
aggregate={}
for group in ['token','pgrust']:
    chosen=[p for p in all_pairs if p['group']==group]
    assert len(chosen)==15
    aggregate[group]={}
    for metric in ['wall','cpu']:
        ratios=[p[metric+'_ratio'] for p in chosen]
        value={'ratios':ratios,'median':statistics.median(ratios),'min':min(ratios),'max':max(ratios)}
        assert value==assessment['aggregate'][group][metric]
        aggregate[group][metric]=value
gates={'token_wall_at_most_0_95':aggregate['token']['wall']['median']<=.95,'token_cpu_below_1':aggregate['token']['cpu']['median']<1,'pgrust_wall_at_most_1_05':aggregate['pgrust']['wall']['median']<=1.05,'pgrust_cpu_at_most_1_05':aggregate['pgrust']['cpu']['median']<=1.05,'every_history_wall_cpu_at_most_1_05':all(h['guard_pass'] for h in histories)}
assert commands['gates']=={'token_wall_max':.95,'token_cpu_strict_max':1,'each_screen_history_wall_cpu_max':1.05,'pgrust_aggregate_wall_cpu_max':1.05,'each_complete_confirmation_wall_cpu_max':1.05}
assert all(gates.values())==assessment['screen_pass'] is False
assert assessment['all_planned_runs_included'] is True and assessment['aa_noise_subtracted'] is False and assessment['diagnostic_samples_included'] is False
assert not (R/'confirmation-controller.json').exists()
for case in frozen['cases']:
    if case['phase']=='confirmation':
        for path in [ROOT/'.work/runs'/case['run_id'],ROOT/'results'/case['run_id'],*map(Path,case['cache_workspaces'].values())]: assert not path.exists()

bind(Path(__file__).resolve())
result={'schema_version':1,'audit_kind':'independent retained-data audit; no harness or assessor execution','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audit_integrity_pass':True,'screen_pass':False,'decision':'PARK: token build-to-ready wall median misses fixed 5% gate','counts':{'controller_calls':12,'histories':6,'primary_commands':144,'check_commands':48,'artifact_receipts':96,'edited_pairs':30},'sources_and_selected_tools':source_details,'recovery':{'original_attempt_wholly_unstarted':True,'original_timeout_preserved_sha256':digest(B/'local-export-adoption-screen-controller.json'),'original_frozen_sha256':digest(B/'local-export-adoption-frozen.json'),'manifest_sha256':digest(R/'recovery.json'),'controller_sha256':digest(R/'screen-controller.json'),'only_scheduling_change':'parent admission wait 300 to 3600 seconds; all harness/verifier argv unchanged','original_absence_receipt_paths':32,'repeated_or_partial_histories':0},'histories':histories,'aggregate':aggregate,'fixed_gates':gates,'all_30_pairs':all_pairs,'all_96_artifact_bindings':artifact_bindings,'scope_notes':['Build readiness includes launcher self/child CPU through validated artifact before VM; execution is excluded.','All cold/wrong/edit/restored samples retained; only the thirty prespecified edit pairs enter gates.','Wrong edits compiled successfully and failed original runtime assertions in native/baseline/candidate; final original states freshly rebuilt and passed.','Selected baseline VM remains distinct from separately recorded build-produced VMs.','No cross-history bytecode-identity or holdout-performance claim.','Public confirmations did not start because the fixed screen gate failed.'],'proofs':PROOFS}
out=Path('/Users/danluu/dev/rust-interp-build-harness-20260912/.work/local-export-screen-audit-20260912/derived.json')
out.write_text(json.dumps(result,indent=2)+'\n')
print('Derived audit ready:',out,'proofs',len(PROOFS),'gates',gates,flush=True)

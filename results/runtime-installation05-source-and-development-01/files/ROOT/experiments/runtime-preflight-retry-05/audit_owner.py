"""Narrow saved owner successor; raw plan and all original predicates retained.

Caller authenticates actual source/control proof and supplies read-only callback
access to current frozen inputs plus the exact completed preparation evidence.
No source import, workload, process, provider or environment observation occurs.
"""
import copy
from pathlib import Path
import environment

ADAPTER = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-preflight-retry-05')
STARTUP_SOURCE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime04-environment-adapter-01')
ROUTES = ADAPTER/'routes.json'
ROUTES_SHA256 = '893d6102741b5206a829e2f5e130614667140b1eacc09d0c55616f7311f82e6a'


def attempt_routes(plan, *, phase, sha, read_json, original, validate_retry_qualification):
    require, same = original.require, original.same
    require(phase == 'preflight' and plan['phase'] == phase, 'retry owner is preflight-only')
    require(plan.get('attempt') == dict(path=str(ROUTES), sha256=ROUTES_SHA256)
        and sha(ROUTES) == ROUTES_SHA256, 'exact authenticated retry descriptor required')
    routes = read_json(ROUTES)
    require(routes['phase'] == phase and routes['attempt_source'] == str(ADAPTER)
        and routes['startup_source'] == str(STARTUP_SOURCE) and routes['installation_entry_gib'] == 24
        and same(plan['capacity'], routes['capacity']), 'exact retry phase/capacity differs')
    require(validate_retry_qualification(copy.deepcopy(plan['retry_qualification'])) is True,
        'separate actual retry controls required')
    return routes


def startup_admission(plan, launch, *, phase, expected, sha, read_json, original,
                      workload_environment, validate_qualification, runtime_started_at, validate_retry_qualification):
    require, same = original.require, original.same
    routes = attempt_routes(plan, phase=phase, sha=sha, read_json=read_json, original=original,
        validate_retry_qualification=validate_retry_qualification)
    proof = plan['startup_environment']
    require(type(proof) is dict and set(proof) == {'derivation', 'policy', 'qualification',
        'preparer', 'preparation_record', 'source_manifest'}, 'exact startup provenance schema required')
    require(same(plan['environment'], workload_environment), 'original workload environment changed')
    planned = environment.validate(workload_environment, proof['derivation'])
    require(same(planned, plan['launch_environment']) and same(planned, launch['environment']),
            'explicit launcher environment differs')
    require(proof['derivation']['platform'] == 'darwin' and proof['derivation']['uid'] == 501,
            'existing Darwin owner context required')
    for role, path in [('policy', STARTUP_SOURCE/'environment.py'), ('preparer', ADAPTER/'prepare.py')]:
        require(proof[role] == dict(path=str(path), sha256=sha(path)),
                'startup source association differs')
    require(validate_qualification(copy.deepcopy(proof['qualification'])) is True,
            'separate actual startup controls required')
    path = Path(routes['preparation_execution'])/'record.json'
    ref = expected['preparation']
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}
        and proof['preparation_record'] == ref['path'] == str(path) and sha(path) == ref['sha256'],
        'actual preparation record reference differs')
    record = read_json(path)
    require(record['status'] == 'finished' and type(record['returncode']) is int and record['returncode'] == 0
        and record['preparation_passed'] is True and record['phase'] == phase and record['cwd'] == str(original.R)
        and record['canonical_owner'] == 'producer-child' and record['signals'] == []
        and record['runtime_admission'] is False and record['compiler_calls'] == record['provider_probes'] == 0,
        'closed read-only preparation required')
    require(all(type(record[k]) is int for k in ['compiler_calls','provider_probes','pid','parent_pid'])
        and record['pid']>0 and record['parent_pid']>0,'typed preparation counters and identities required')
    require(same(record['environment'], proof['derivation']['passed']), 'actual passed preparation environment differs')
    require(record['producer_command'][2] == str(ADAPTER/'prepare.py'), 'actual preparer route differs')
    args = record['producer_command'][3:]
    def argument(name):
        require(args.count(name) == 1 and args.index(name)+1 < len(args), 'missing unique preparation argument')
        return args[args.index(name)+1]
    require(argument('--phase') == phase and argument('--preparation-record') == str(path)
        and same(environment.decode(argument('--preparation-passed-environment-json')),record['environment'])
        and argument('--startup-audit-sha256') == proof['qualification']['audit']['sha256']
        and argument('--retry-audit-sha256') == plan['retry_qualification']['audit']['sha256']
        and argument('--startup-source-manifest') == proof['source_manifest']['path']
        and argument('--startup-source-manifest-sha256') == proof['source_manifest']['sha256'],
        'actual preparation startup arguments differ')
    source = expected['preparation_launcher']
    require(set(source) == {'path','sha256'} and record['command'][2] == source['path']
        and record['source_sha256'] == source['sha256'] == sha(source['path']) == sha(path.parent/'launcher.py'),
        'actual preparation launcher source differs')
    observation_path = path.parent/'child-observation.json'
    require(record['child_observation_sha256'] == sha(observation_path), 'preparation observation digest differs')
    observed = read_json(observation_path)
    require(observed['status'] == 'returned' and observed['pid'] == record['pid']
        and observed['parent_pid'] == record['parent_pid'] and observed['blocked_events'] == []
        and same(observed['command'], record['producer_command']), 'actual preparation child observation differs')
    require(record['started_at'] <= record['child_started_at'] <= observed['started_at']
        <= observed['finished_at'] <= record['finished_at'] <= record['readback_finished_at'] <= runtime_started_at,
        'actual preparation chronology differs')
    maps = observed['environments']
    require(same(maps['passed'], record['environment']), 'child passed environment differs')
    samples = proof['derivation']['observations']
    require(same(maps['before_producer_imports'], samples['before_factory_definitions'])
        and same(maps['at_return_or_failure'], samples['before_packet']),
        'raw preparation observations differ')
    packet = Path(routes['packet'])
    for name in ['plan.json', 'inputs.json', 'launch.json']:
        require(record['outputs'][name]['sha256'] == sha(packet/name), 'actual preparation output differs')
    invocation = record['invocation']
    require(set(invocation) == {'path','sha256'} and sha(invocation['path']) == invocation['sha256'],
            'preparation invocation differs')
    invocation_value = read_json(invocation['path'])
    require(same(invocation_value['adapter'], dict(preparer=proof['preparer'],
        source_manifest=proof['source_manifest'],startup_controls=proof['qualification']['audit'],
        retry_controls=plan['retry_qualification']['audit'])),
        'actual invoked startup source association differs')
    manifest=proof['source_manifest']
    require(set(manifest)=={'path','sha256'} and sha(manifest['path'])==manifest['sha256'],
            'startup source manifest differs')
    source_rows=read_json(manifest['path'])
    require(set(source_rows)=={'status','files'} and source_rows['status']=='reviewed-runtime-preflight05-startup-source-closure',
            'startup source manifest schema differs')
    for role in ['policy','preparer']:
        require(source_rows['files'][proof[role]['path']]['sha256']==proof[role]['sha256'],
                'startup source omitted from actual manifest')
    require(source_rows['files'][str(ROUTES)]['sha256'] == ROUTES_SHA256,
        'retry descriptor omitted from actual source manifest')
    for name in ['entry.py','controller.py','audit_owner.py','prepare_once.py','launch.py']:
        require(source_rows['files'][str(ADAPTER/name)]['sha256'] == sha(ADAPTER/name),
            'retry admission source omitted from actual manifest')
    return copy.deepcopy(proof)


def owner(plan, launch, terminal, outer, launcher, *, phase, expected, sha, read_json, original, workload_environment, validate_qualification, validate_retry_qualification):
    """Bind the original completed owner; never manufacture a passed terminal."""
    require, same, R = original.require, original.same, original.R
    routes = attempt_routes(plan, phase=phase, sha=sha, read_json=read_json, original=original,
        validate_retry_qualification=validate_retry_qualification)
    paths = dict(packet=Path(routes['packet']), work=Path(routes['work']),
        outer=Path(routes['supervisor']), report=Path(routes['report']))
    packet, work = paths['packet'], paths['work']
    require(plan['phase'] == terminal['phase'] == phase and plan['owner'] == str(R)
            and plan['work'] == str(work) and plan['supervisor_work'] == str(paths['outer']),
            'exact runtime phase/owner paths required')
    require(terminal['status'] == 'passed' and type(terminal['pid']) is int
            and type(terminal['parent_pid']) is int and terminal['pid'] > 0 and terminal['parent_pid'] > 0,
            'actual passed runtime owner required')
    for name in ['application_qualified', 'performance_measurement', 'exporter_qualified', 'std_mir_prepared']:
        require(terminal[name] is False, 'unearned runtime qualification scope')
    require(sha(packet/'launch.json') == expected['launch']
            and terminal['inputs_sha256'] == launch['inputs_sha256'] == expected['inputs'] == sha(packet/'inputs.json')
            and terminal['plan_sha256'] == launch['plan_sha256'] == sha(packet/'plan.json')
            and terminal['snapshot_plan_sha256'] == launch['snapshot_plan_sha256'] == expected['snapshot_plan']
            and sha(packet/'snapshot-plan.json') == expected['snapshot_plan']
            and sha(work/'receipt.json') == expected['receipt'], 'actual packet/terminal association differs')
    startup_admission(plan, launch, phase=phase, expected=expected, sha=sha, read_json=read_json,
        original=original, workload_environment=workload_environment, validate_qualification=validate_qualification,
        runtime_started_at=terminal['started_at'],validate_retry_qualification=validate_retry_qualification)
    require(launch['cwd'] == str(R) and launch['environment'] == plan['launch_environment']
            and launch['capacity'] == plan['capacity'] == dict(entry_gib=16, stop_gib=9, floor_gib=8,
                combined_namespace_bytes=14*2**30, evidence_bytes=256*2**20), 'runtime context or limits changed')
    require(outer['status'] == 'finished' and type(outer['returncode']) is int and outer['returncode'] == 0
            and outer['child_pid'] == terminal['pid'] and outer['supervisor_pid'] == terminal['parent_pid']
            and outer['command'] == launch['command'][6:] and outer['cwd'] == str(R)
            and outer['plan_sha256'] == sha(paths['outer']/'plan.json')
            and outer['log_sha256'] == sha(paths['outer']/'command.log'), 'actual runtime supervisor closure differs')
    require(outer['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at']
            <= terminal['finished_at'] <= outer['finished_at']
            and terminal['free_bytes_before'] >= 16*2**30 and terminal['free_bytes_after'] >= 9*2**30,
            'actual runtime admission/timing differs')
    # New launchers must follow the already reviewed actual hash launch schema.
    # Old legacy wrapper-only "finished" records are not relabeled as closure.
    require(launcher['status'] == 'terminal-observed' and type(launcher['returncode']) is int
            and launcher['returncode'] == 0 and type(launcher['launcher_returncode']) is int
            and launcher['launcher_returncode'] == 0 and launcher['outer_sha256'] == sha(paths['outer']/'status.json')
            and launcher['command'] == launch['command'] and launcher['cwd'] == str(R)
            and same(launcher['environment'], launch['environment']) and launcher['launch_sha256'] == expected['launch']
            and launcher['started_at'] <= launcher['launcher_finished_at'] <= launcher['finished_at']
            and outer['finished_at'] <= launcher['terminal_observed_at'] <= launcher['finished_at'],
            'explicit runtime launcher terminal observation required')
    launcher_path = Path(expected['launcher_record'])
    require(launcher_path == Path(routes['launcher_execution'])/'record.json'
            and sha(launcher_path) == expected['launcher_record_sha256']
            and sha(launcher['launcher_source_path']) == launcher['launcher_source_sha256'],
            'reviewed actual launcher record/source binding differs')
    for stream in ['stdout', 'stderr']:
        require(sha(launcher_path.parent/stream) == launcher[stream+'_sha256'], 'launcher raw differs')
    handoff = read_json(launcher_path.parent/'stdout')
    require(handoff['directory'] == str(paths['outer'])
            and handoff['supervisor_pid'] == outer['supervisor_pid'] == launcher['supervisor_pid']
            and launcher['controller_pid'] == terminal['pid'], 'actual runtime launcher handoff differs')
    return paths

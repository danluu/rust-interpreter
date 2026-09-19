"""Pure saved-data calculation for PROTOCOL.md, after both ordinary verifiers.

This module starts no processes and reads no providers. The future caller must
authenticate these documents and the two successful owner/verifier closures.
No owner schema or future receipt digest is invented here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

MODES = ('native', 'baseline', 'candidate')
CUSTOM = MODES[1:]
STATES = ((0, 0, 'cold'), (0, -1, 'wrong-edit'),
          *((0, n, 'edit') for n in range(1, 6)), (1, -2, 'restored-original'))
FLAGS = ['-Zmir-opt-level=3', '-Zhir-body-cache-capture=false', '-Zhir-body-cache-reuse=false']
BUILD = ('build_to_ready_seconds', 'build_to_ready_cpu_seconds', 'cargo_cpu_seconds')
STAGES = ('cargo_seconds', 'execution_seconds', 'artifact_hash_seconds', 'launcher_seconds')
BASELINE = dict(tool_key='7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a',
    runtime_key='eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03',
    std_key='e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63')
CANDIDATE = dict(runtime_key='f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70',
    std_key='f6366b5873636f47cdc3e9941a9b24ef612f94432baecb5d75ed5c4c54911928')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value, *, zero=False):
    require(type(value) in (int, float) and math.isfinite(value)
            and (value >= 0 if zero else value > 0), 'finite positive timing required')
    return value


def sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'exact SHA/key required')
    return value


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def pair(rows, state):
    selected = {m: rows[0, state, m] for m in MODES}
    before, after = selected['baseline'], selected['candidate']
    result = dict(cycle=0, state=state, source_sha256=before['source_sha256'],
        difference_seconds=after['seconds']-before['seconds'],
        cpu_difference_seconds=after['cpu_seconds']-before['cpu_seconds'],
        identical_bytecode=True, stage_seconds={m: {field: sum(
            number(c['launch'][field], zero=True) for c in selected[m]['calls'])
            for field in STAGES} for m in CUSTOM})
    for mode in MODES:
        for field in ('seconds', 'cpu_seconds') + (BUILD if mode in CUSTOM else ()):
            result[mode+'_'+field] = selected[mode][field]
    for field in BUILD[:2]:
        result[field.removesuffix('_seconds')+'_difference_seconds'] = after[field]-before[field]
    return result


def history(summary, records, verification, arms, *, aa):
    require(type(records) is list and len(records) == 24, 'exact complete24 history required')
    require(all(type(verification[k]) is int for k in ('schema_version', 'commands', 'cycles', 'edited_pairs'))
            and verification['schema_version'] == 1 and verification['commands'] == 24
            and verification['cycles'] == 1 and verification['edited_pairs'] == 5,
            'ordinary verification counts differ')
    for key in ('measurement_controls_verified', 'build_to_ready_metrics_verified',
                'restored_original_build_and_execution_verified', 'paired_bytecode_identical'):
        require(verification[key] is True, 'ordinary verification failed: '+key)
    if aa:
        require(verification['identical_build_isolated_caches_verified'] is True,
                'A/A isolated-cache verification missing')
    require(summary['project'] == 'ruff' and summary['schema_version'] == 2
            and type(summary['cycles']) is int and summary['cycles'] == 1
            and len(summary['edits']) == 5 and summary['batch'] is True,
            'fixed Ruff history differs')
    require(summary.get('aa_control', False) is aa
            and summary['initial_mode_order'] == (['candidate', 'native', 'baseline'] if aa else list(MODES)),
            'fixed history kind/order differs')
    for key in ('test_source_unchanged', 'wrong_production_edit_rejected'):
        require(summary[key] is True, 'required history control failed')
    for key in ('compare_isolated_batches', 'cargo_timings', 'vary_selection',
                'trap_unsupported_calls', 'run_try_callbacks'):
        require(summary[key] is False, 'forbidden history setting: '+key)
    require(summary.get('check_floor') is None and summary['instruction_limit'] == 1000000000
            and summary['allocation_limit'] == 150000 and summary['build_jobs'] == 2
            and summary['custom_build_jobs'] == dict(baseline=2, candidate=2), 'fixed limits/jobs differ')
    native = summary['native_control']
    require(native['profile'] == 'repository' and native['jobs'] == 2 and native['test_threads'] == '1'
            and native['toolchain'] == 'nightly-2026-09-08', 'fixed native control differs')
    tests = summary['tests']
    require(type(tests) is list and len(tests) == len(set(tests)) == 6
            and all(type(t) is str and t for t in tests), 'exact six test selections required')
    sha(summary['case_sha256'])
    comparison = summary['comparison']
    require(comparison['engine'] == 'jit' and comparison['identical_bytecode_required'] is True,
            'strict paired bytecode setting required')
    for mode in CUSTOM:
        tool = summary['tool_builds'][mode]; arm = summary['runtime_arms']['arms'][mode]
        expected = arms[mode]
        require(tool['tool_key'] == comparison[mode+'_tool_key'] == arm['tool_key'] == expected['tool_key']
                and arm['runtime']['key'] == expected['runtime_key']
                and arm['prepared_std']['key'] == summary['std_mir_by_mode'][mode]['key'] == expected['std_key'],
                'immutable arm selection differs')
        require(tool['engine'] == 'jit' and tool['guest_rustflags'] == FLAGS, 'guest compiler flags differ')
        for key in ('inline_leaves', 'jit_resumable_calls', 'jit_persistent_registers'):
            require(tool[key] is True, 'required JIT option differs')
        for key in ('jit_native_calls', 'jit_native_call_stubs', 'trap_unsupported_calls', 'run_try_callbacks'):
            require(tool[key] is False, 'forbidden JIT/compatibility option')
    require(len(set(summary['cache_workspaces'].values())) == 2
            and set(summary['cache_workspaces']) == set(CUSTOM), 'isolated custom caches required')
    if aa:
        require(summary['tool_builds']['baseline'] == summary['tool_builds']['candidate'], 'A/A tools differ')

    rows = {}
    for row in records:
        require(type(row['cycle']) is int and type(row['state']) is int, 'integer sample identity required')
        key = row['cycle'], row['state'], row['mode']
        require(key not in rows, 'duplicate raw sample')
        rows[key] = row
        for field in ('seconds', 'cpu_seconds'):
            number(row[field])
        sha(row['source_sha256'])
        require(row['tests'] == tests and type(row['calls']) is list and len(row['calls']) == 1,
                'fixed batched test call differs')
        call = row['calls'][0]; code = call['returncode']
        require(type(code) is int and (code > 0 if row['state'] == -1 else code == 0),
                'unexpected call outcome')
        if row['mode'] in CUSTOM:
            require(row['engine'] == 'jit' and row['tool_key'] == arms[row['mode']]['tool_key'], 'raw arm differs')
            for field in BUILD:
                number(row[field], zero=field == 'cargo_cpu_seconds')
            require(len(row['artifacts']) == 1, 'one executed batched RBC required')
            sha(row['artifacts'][0]['sha256'])
            for field in ('function_cache', 'borrowck_cache'):
                require(call['launch'][field] == 'off', 'ordinary cache setting differs')
    require(set(rows) == {(c, s, m) for c, s, _ in STATES for m in MODES}, 'missing/unexpected raw sample')
    require(same(summary['samples'], [{k: v for k, v in row.items() if k != 'calls'} for row in records]),
            'summary samples differ from raw history')
    sources = {}
    for cycle, state, phase in STATES:
        group = [rows[cycle, state, mode] for mode in MODES]
        require(all(r['phase'] == phase for r in group) and len({r['source_sha256'] for r in group}) == 1,
                'paired source/phase differs')
        require(group[1]['artifacts'][0]['sha256'] == group[2]['artifacts'][0]['sha256'], 'paired RBC differs')
        sources[state] = group[0]['source_sha256']
    require(len({sources[n] for n in (0, -1, 1, 2, 3, 4, 5)}) == 7 and sources[-2] == sources[0],
            'complete distinct edits and restoration required')
    require(summary['restored_original'] == dict(verified=True, source_sha256=sources[0], cycle=1,
            state=-2, commands=3, excluded_from_edited_medians=True), 'restoration receipt differs')
    pairs = [pair(rows, state) for state in range(1, 6)]
    require(same(summary['comparison']['pairs'], pairs), 'summary paired fields differ from raw observations')
    ratios = [number(p['candidate_seconds']/p['baseline_seconds']) for p in pairs]
    totals = {phase: {mode: {field: sum(r[field] for r in records if r['phase'] == phase and r['mode'] == mode)
                for field in ('seconds', 'cpu_seconds')} for mode in MODES}
              for phase in ('cold', 'wrong-edit', 'edit', 'restored-original')}
    for phase in totals.values():
        for mode in phase.values():
            for value in mode.values():
                number(value)
    complete = {field: number(sum(r[field] for r in records)) for field in ('seconds', 'cpu_seconds')}
    return dict(ratios=ratios, pairs=pairs, samples=summary['samples'], subtotals=totals,
        all_command_totals=complete,
        build_to_ready_ratios=[number(p['candidate_build_to_ready_seconds']/p['baseline_build_to_ready_seconds']) for p in pairs],
        inherited_std_preparation=summary['std_mir_by_mode'], source_by_state=sources)


def assess(ab, aa, candidate_tool_key):
    """Calculate only; authenticated successful owner closures remain a caller gate."""
    candidate = CANDIDATE | dict(tool_key=sha(candidate_tool_key))
    require(candidate_tool_key != BASELINE['tool_key'], 'A/B candidate must be separately bound')
    output = {name: history(value['summary'], value['records'], value['verification'], arms, aa=name == 'aa')
        for name, value, arms in [('ab', ab, dict(baseline=BASELINE, candidate=candidate)),
                                  ('aa', aa, dict(baseline=BASELINE, candidate=BASELINE))]}
    for field in ('case_sha256', 'revision', 'tests', 'edits', 'scripts_sha256'):
        require(ab['summary'][field] == aa['summary'][field], 'cross-history source/case differs: '+field)
    require(output['ab']['source_by_state'] == output['aa']['source_by_state'], 'cross-history source states differ')
    tools = [value['summary']['tool_builds'][mode] for value in (ab, aa) for mode in CUSTOM]
    settings = [{k: v for k, v in tool.items() if k not in ('tool_key', 'exporter_sha256')} for tool in tools]
    require(all(item == settings[0] for item in settings), 'VM or execution settings differ across arms')
    require(ab['summary']['tool_builds']['baseline'] == aa['summary']['tool_builds']['baseline'],
            'original baseline tool identity changed')
    caches = [p for value in (ab, aa) for p in value['summary']['cache_workspaces'].values()]
    require(len(set(caches)) == 4, 'histories share custom caches')
    b = statistics.median(output['ab']['ratios'])
    deviations = [abs(ratio-1) for ratio in output['aa']['ratios']]
    v = statistics.median(deviations)
    require(math.isfinite(b+v), 'nonfinite criterion')
    return dict(histories=output, B=b, V=v, B_plus_V=b+v, aa_absolute_deviations=deviations,
        criterion_met=b+v < 1, decision='advance' if b+v < 1 else 'park',
        criterion='median(AB candidate/baseline) + median(abs(AA candidate/baseline - 1)) < 1',
        owner_closures=None, session_totals=None, actual_input_refs=None,
        qualification_gate_complete=False, performance_target_met=False, final_latency_qualified=False,
        notes=['Owner/verifier process closure and exact input hashes must be bound by the future caller.',
               'Cold, wrong-edit and restoration costs are retained and excluded from the criterion.',
               'Build-to-ready ratios are separate; no execution time is subtracted.',
               'Inherited std setup/build times are historical costs, not measured current setup.'])


def owner_closure(parent, outer, observer, result, history):
    """Require the distinct parent OS wait and the observer's saved terminal."""
    require(parent['history'] == observer['history'] == result['history'] == history
            and parent['status'] == outer['status'] == 'finished'
            and observer['status'] == result['status'] == 'passed'
            and parent['observer_verified'] is True
            and parent['supervisor_may_be_live'] is False and parent['controller_may_be_live'] is False,
            'normal parent and observer closure required')
    for value in (parent['returncode'], parent['controller_returncode'], outer['returncode']):
        require(type(value) is int and value == 0, 'successful process closure required')
    require(not any('error' in row or 'execution_error' in row for row in (parent, outer, observer, result)),
            'saved owner error present')
    require(parent['pid'] == outer['supervisor_pid'] == observer['parent_pid']
            and parent['parent_pid'] == outer['supervisor_parent_pid']
            and outer['child_pid'] == observer['pid'], 'owner PID association differs')
    for row, fields in ((parent, ('pid', 'parent_pid')), (observer, ('pid', 'parent_pid'))):
        require(all(type(row[f]) is int and row[f] > 0 for f in fields), 'actual positive PID required')
    times = [parent['started_at'], outer['started_at'], observer['started_at'],
             observer['finished_at'], outer['finished_at'], parent['finished_at']]
    require(all(number(t) for t in times) and times == sorted(times), 'owner chronology differs')
    require(parent['plan'] == observer['plan'] == result['plan']
            and parent['result'] == observer['result']
            and observer['observer_os_closure_observed'] is result['observer_os_closure_observed'] is False
            and observer['performance_qualified'] is result['performance_qualified'] is False,
            'owner proof association or scope differs')
    cpu = parent['child_cpu']
    require(number(cpu['total_seconds'], zero=True) == number(cpu['user_seconds'], zero=True)
            + number(cpu['system_seconds'], zero=True), 'parent CPU accounting differs')
    return dict(wall_seconds=number(parent['session_wall_seconds']), child_cpu=cpu,
        scope='Supervisor session including admission queues, runner, verification and observer overhead; excludes parent CPU.')


def main():
    """Read only exact closed evidence; never invoke the runner or verifier."""
    parser = argparse.ArgumentParser(__doc__)
    for name in ('ab-parent-sha256', 'aa-parent-sha256', 'transport-sha256', 'assessor-sha256', 'candidate-tool-key'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    r = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
    launch_dir = here.parent/'ruff-screen-launch-01'
    transport = launch_dir/'screen-launch.py'
    inputs = {}

    def read(ref, *, raw=False):
        require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'exact input reference required')
        path = Path(ref['path']); sha(ref['sha256'])
        require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
                and path.stat().st_size <= 32*2**20, 'bounded ordinary evidence required')
        before = path.stat()
        data = path.read_bytes(); after = path.stat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
        require(all(getattr(before, f) == getattr(after, f) for f in fields)
                and hashlib.sha256(data).hexdigest() == ref['sha256'], 'saved evidence changed')
        require(str(path) not in inputs or inputs[str(path)] == ref['sha256'], 'overlapping input changed')
        inputs[str(path)] = ref['sha256']
        return data if raw else json.loads(data)

    def at(path, digest):
        return dict(path=str(path), sha256=digest)

    read(at(Path(__file__).resolve(), args.assessor_sha256), raw=True)
    read(at(transport, args.transport_sha256), raw=True)
    histories, owners, sessions, saved = {}, {}, {}, {}
    for name in ('ab', 'aa'):
        run_id = 'hir-options-hash-ruff-screen-'+name+'-01'
        execution, work = r/'.work'/(run_id+'-execution'), r/'.work'/(run_id+'-observer')
        outer_dir = r/'.work/experiments'/(run_id+'-supervisor')
        parent_ref = at(execution/'record.json', getattr(args, name+'_parent_sha256'))
        parent = read(parent_ref)
        require(parent['source_sha256'] == args.transport_sha256 and parent['cwd'] == str(r), 'parent source/root differs')
        for field, path in (('outer', outer_dir/'status.json'), ('observer', work/'receipt.json'), ('result', work/'result.json')):
            require(parent[field]['path'] == str(path), 'closed owner route differs')
        outer, observer, result = [read(parent[field]) for field in ('outer', 'observer', 'result')]
        sessions[name] = owner_closure(parent, outer, observer, result, name)
        require(parent['launch']['path'] == str(launch_dir/'packet-01'/('launch-'+name+'.json'))
                and parent['sources']['path'] == str(launch_dir/'sources.json')
                and parent['plan']['path'] == str(launch_dir/'packet-01/plan.json')
                and parent['outer_plan']['path'] == str(outer_dir/'plan.json'), 'prepared input route differs')
        launch, sources, plan, outer_plan = [read(parent[field]) for field in ('launch', 'sources', 'plan', 'outer_plan')]
        h = plan['histories'][name]
        require(parent['command'] == launch['argv']
                and parent['environment'] == observer['environment'] == launch['environment'] == h['environment']
                and parent['outer_plan'] == launch['plan'] and plan['sources'] == parent['sources']
                and outer_plan['command'] == outer['command'] and outer['plan_sha256'] == parent['outer_plan']['sha256']
                and outer['owner'] == outer_plan['owner'] == str(r), 'prepared launch/owner association differs')
        read(at(r/'scripts/supervise_experiment.py', outer_plan['supervisor_sha256']), raw=True)
        for path in (launch_dir/'observe.py', launch_dir/'prepare.py'):
            read(at(path, sources['files'][str(path)]), raw=True)
        read(at(outer_dir/'command.log', outer['log_sha256']), raw=True)
        for channel in ('stdout', 'stderr'):
            read(at(execution/channel, parent[channel+'_sha256']), raw=True)
        documents = {}
        for field, path in (('summary', r/'results'/run_id/'summary.json'),
                            ('records', r/'.work/runs'/run_id/'records.json'),
                            ('verification', r/'results'/run_id/'verification.json')):
            require(result[field]['path'] == str(path) == h[field], 'saved document route differs')
            documents[field] = read(result[field])
        require(observer['child_receipts'] == [result['runner'], result['verifier']], 'ordinary child receipts differ')
        previous = observer['started_at']
        for child_name in ('runner', 'verifier'):
            child_ref = result[child_name]
            require(child_ref['path'] == str(work/child_name/'receipt.json'), 'ordinary child route differs')
            child = read(child_ref)
            require(child['status'] == 'finished' and type(child['returncode']) is int and child['returncode'] == 0
                    and child['supervisor_pid'] == observer['pid'] and child['parent_pid'] == observer['parent_pid']
                    and child['command'] == h['command' if child_name == 'runner' else 'verifier']
                    and child['cwd'] == str(r) and child['environment'] == h['environment']
                    and previous <= child['started_at'] <= child['finished_at'] <= observer['finished_at'],
                    'ordinary child closure/command differs')
            previous = child['finished_at']
            streams = {channel: read(at(work/child_name/channel, child[channel+'_sha256']), raw=True)
                       for channel in ('stdout', 'stderr')}
            if child_name == 'verifier':
                require(json.loads(streams['stdout']) == documents['verification'] and not streams['stderr']
                        and result['canonical_verification']['admitted_at'] <= child['started_at']
                        <= child['finished_at'] <= result['canonical_verification']['released_at'],
                        'ordinary verification output/lock association differs')
        histories[name] = documents
        owners[name] = dict(parent=parent_ref, outer=parent['outer'], observer=parent['observer'], result=parent['result'])
        saved[name] = dict(parent=parent, result=result, plan=plan)
    ab, aa = saved['ab'], saved['aa']
    require(ab['parent']['plan'] == aa['parent']['plan'] and ab['parent']['sources'] == aa['parent']['sources']
            and ab['parent']['finished_at'] <= aa['parent']['started_at'], 'fixed AB then AA order differs')
    previous = aa['result']['previous']
    require(ab['result']['previous'] is None and previous['ab_result'] == owners['ab']['result']
            and previous['ab_receipt'] == owners['ab']['observer'] and previous['ab_outer'] == owners['ab']['outer'],
            'AA predecessor differs')
    retirement = read(previous['retirement_review'])
    require(retirement['status'] == 'verified' and retirement['ab_result'] == owners['ab']['result']
            and retirement['ab_outer'] == owners['ab']['outer']
            and retirement['selected_roots'] == ab['result']['generated_cache_roots']
            and retirement['preserved_evidence'] == [ab['result'][k] for k in ('summary', 'records', 'verification')]
            and ab['parent']['finished_at'] <= retirement['finished_at'] <= aa['parent']['started_at']
            and retirement['retirement_proofs'], 'reviewed AB retirement differs')
    for proof in retirement['retirement_proofs']:
        read(proof)
    output = assess(histories['ab'], histories['aa'], args.candidate_tool_key)
    for path, digest in list(inputs.items()):
        read(at(path, digest), raw=True)
    output.update(owner_closures=owners, session_totals=sessions, actual_input_refs=inputs,
                  qualification_gate_complete=True)
    output['notes'][0] = 'Both ordinary verifiers and normal parent/outer/observer closures are bound to exact saved input hashes.'
    with args.output.open('x') as stream:
        json.dump(output, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()

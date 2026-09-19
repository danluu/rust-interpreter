"""Read back the actual16 + failed7 + successful3 histories without relabeling.

No compiler execution, missing-output inference, or alternate predecessor is
available here. The successor must already have passed its source-derived
27/18 tests and retained its explicit saved-cwd limitation.
"""
import json
from pathlib import Path
import re

from compose_sysroot import require, digest


def child_outcome(child, *, failed_support):
    require(child['status'] == ('failed' if failed_support else 'finished')
            and child['returncode'] == (1 if failed_support else 0) and child['expected'] == [0],
            'actual child outcome differs')
    if failed_support:
        require(child['error'] == "AssertionError('unexpected compiler-stage return code')",
                'failed support child error was relabeled')


def joined_commands(first, second, final, compiled):
    """Keep failed actual work distinct from the successful logical recipe."""
    require([len(first), len(second), len(final)] == [16, 7, 3], 'three history lengths differ')
    successful = [*first, *second[:6], *final]
    complete = [*first, *second, *final]
    require(len({row['path'] for row in complete}) == len(complete),
            'actual child receipt reused across owning histories')
    require(compiled['saved_children'] == 22 and compiled['saved_actual_children'] == 23
            and compiled['actual_continuation_children'] == 3
            and compiled['command_history'] == successful
            and compiled['actual_command_history'] == complete
            and compiled['failed_support_attempt'] == second[6],
            'logical success and complete actual histories differ')
    return successful, complete


def validate(*, owner, source, evidence, source_directory, frozen, sha, derive_tests):
    owner, source, evidence, source_directory = map(Path, [owner, source, evidence, source_directory])
    old = owner/'.work/hir-options-hash-compiler-build-02'
    old_source = owner/'experiments/hir-options-hash/compiler-build-02'
    middle = owner/'.work/hir-options-hash-compiler-build-continuation-01'
    middle_source = owner/'experiments/hir-options-hash/compiler-build-continuation-01'
    require(evidence == owner/'.work/hir-options-hash-compiler-build-continuation-03'
            and source_directory == owner/'experiments/hir-options-hash/compiler-build-continuation-03',
            'exact compiler continuation route required')
    def read(path):
        path = frozen(path)
        require(path.stat().st_size <= 256*2**20, 'bounded predecessor JSON required')
        return json.loads(path.read_bytes())
    plan = read(source_directory/'plan.json'); freeze = read(source_directory/'inputs.json')
    previous_plan = read(middle_source/'plan.json'); previous_freeze = read(middle_source/'inputs.json')
    original = read(old_source/'plan.json'); prior_freeze = read(old_source/'inputs.json')
    terminal = read(evidence/'receipt.json'); failed = read(old/'receipt.json')
    middle_failed = read(middle/'receipt.json'); compiled = read(evidence/'compiled.json')
    require(sha(source_directory/'plan.json') == freeze['plan_sha256']
            and sha(middle_source/'plan.json') == previous_freeze['plan_sha256'] == plan['previous_continuation']['plan_sha256']
            and sha(middle_source/'inputs.json') == plan['previous_continuation']['inputs_sha256']
            and sha(old_source/'plan.json') == prior_freeze['plan_sha256'] == plan['saved']['plan_sha256']
            and sha(old_source/'inputs.json') == plan['saved']['inputs_sha256'], 'compiler plans/freeze differ')
    expected_children = json.loads(json.dumps(original['children']))
    require(expected_children[22]['argv'] == ['./x', 'build', '--stage', '1', 'src/tools/run-make-support', '--jobs', '2', '-vv'],
            'original support route differs')
    expected_children[22]['argv'][1] = 'test'
    require(previous_plan['original_plan'] == original and previous_plan['children'] == original['children']
            and previous_plan['remaining_children'] == original['children'][16:]
            and plan['children'] == expected_children and plan['remaining_children'] == expected_children[22:]
            and plan['stages'][:7] == original['stages'][:7] and plan['stages'][7] == expected_children[22]
            and plan['saved'] == previous_plan['saved']
            and plan['test_source'] == previous_plan['test_source'] == derive_tests(source, original['tests'])
            and plan['tests'] == previous_plan['tests'] == plan['test_source']['tests'],
            'source-derived test expectations or narrow registered support route differ')
    require(failed['status'] == 'failed' and failed['compiler_stages_completed'] == 2 and len(failed['commands']) == 16,
            'original failed16 history differs')
    require(middle_failed['status'] == 'failed' and middle_failed['compiler_stages_completed'] == 7
            and middle_failed['new_compiler_stages_completed'] == 5 and middle_failed['saved_children'] == 16
            and len(middle_failed['commands']) == 7
            and middle_failed['error'] == "AssertionError('unexpected compiler-stage return code')",
            'retained failed support attempt differs')
    require(terminal['status'] == 'passed' and terminal['compiler_stages_completed'] == 8
            and terminal['new_compiler_stages_completed'] == 1 and terminal['saved_children'] == 22
            and terminal['saved_actual_children'] == 23 and len(terminal['commands']) == 3,
            'exact three-child support continuation success required')
    for record in [failed, middle_failed, terminal]:
        require(not any(record[key] for key in ['native_recipe_qualified', 'hash_driver_qualified', 'application_qualified']),
                'compiler predecessor wrongly claims downstream qualification')
    require(sha(old/'receipt.json') == plan['saved']['receipt_sha256'] == terminal['prior_failed_build_sha256']
            == middle_failed['prior_failed_build_sha256'] == compiled['prior_failed_build_sha256']
            and sha(middle/'receipt.json') == plan['previous_continuation']['receipt_sha256']
            == terminal['prior_failed_continuation_sha256'] == compiled['prior_failed_continuation_sha256']
            and sha(evidence/'compiled.json') == terminal['compiled_sha256'],
            'continued compiler receipt association differs')
    successful, complete = joined_commands(failed['commands'], middle_failed['commands'], terminal['commands'], compiled)
    require(compiled['status'] == 'compiled-awaiting-native-recipe-and-B3-qualification'
            and compiled['stages'] == 8 and compiled['all_lowering_tests'] == 27 and compiled['all_interface_tests'] == 18
            and compiled['all_support_tests'] == 15 and compiled['saved_children'] == 22
            and compiled['saved_actual_children'] == 23 and compiled['actual_continuation_children'] == 3
            and compiled['command_history'] == successful and len(successful) == 25
            and compiled['actual_command_history'] == complete and len(complete) == 26
            and compiled['failed_support_attempt'] == middle_failed['commands'][6],
            'logical success and complete actual histories differ')
    for record in [failed, middle_failed, terminal, compiled]:
        require(record['candidate_revision'] == plan['candidate_revision']
                and record['source_identity'] == plan['source_identity'], 'continued source identity differs')
    require(failed['finished_at'] <= middle_failed['admitted_at']
            and middle_failed['finished_at'] <= terminal['admitted_at'], 'compiler histories overlap or are reordered')
    # Native observations are copied saved evidence, not new probes in the last
    # support-only continuation. Bind both bytes and their original role/path.
    require(compiled['native_loader_original_path'] == str(middle/'stage1-native-loader.json'),
            'saved native loader origin was relabeled')
    for name in ['stage1-inventory.json', 'stage1-native-loader.json']:
        frozen(middle/name); frozen(evidence/name)
        require(sha(middle/name) == sha(evidence/name), 'saved native observation copy differs')
    for field, name in [('native_loader_sha256', 'stage1-native-loader.json'),
                        ('run_make_support_sha256', 'run-make-support-inventory.json'),
                        ('run_make_support_producer_sha256', 'run-make-support-producer.json')]:
        frozen(evidence/name)
        require(compiled[field] == sha(evidence/name), 'actual final output catalog binding differs')
    streams, unavailable_cwd = {}, []
    for root, outer, start, rows, refs in [
        (old, failed, 0, original['children'][:16], failed['commands']),
        (middle, middle_failed, 16, previous_plan['remaining_children'][:7], middle_failed['commands']),
        (evidence, terminal, 23, plan['remaining_children'], terminal['commands']),
    ]:
        last = outer['admitted_at']
        for local_index, (wanted, ref) in enumerate(zip(rows, refs, strict=True)):
            global_index = start+local_index
            receipt = root/'commands'/f'{local_index:03}'/'receipt.json'
            child = read(receipt)
            require(ref == dict(path=str(receipt), sha256=sha(receipt), pid=child['pid'], command=wanted['argv']),
                    'exact actual child reference differs')
            failed_support = root == middle and local_index == 6
            child_outcome(child, failed_support=failed_support)
            require(child['command'] == wanted['argv'] and child['cwd'] == wanted['cwd'] == str(source)
                    and child['environment'] == wanted['environment'] and child['supervisor_pid'] == outer['pid']
                    and child['parent_pid'] == outer['parent_pid']
                    and last <= child['started_at'] <= child['finished_at'] <= outer['finished_at'],
                    'actual child belongs to a different invocation/time/environment')
            last = child['finished_at']
            identity = child['identity']; ps = identity['ps'].splitlines()
            require(identity['ps_returncode'] == 0 and len(ps) == 1
                    and ps[0].split()[:3] == [str(child['pid']), str(outer['pid']), str(child['pid'])]
                    and ps[0].endswith(' '.join(wanted['argv'])), 'actual child PID/parent/session/command differs')
            if identity['cwd_returncode'] != 0 or not identity['cwd']:
                require(identity['cwd_returncode'] == 1 and not identity['cwd'], 'unknown contemporaneous cwd failure')
                unavailable_cwd.append(global_index)
            else:
                require('n'+str(source) in identity['cwd'].splitlines(), 'actual cwd evidence differs')
            require(child['samples'] and all(not sample['allocation_errors'] and sample['free_bytes'] >= 9*2**30
                    and sample['namespace_allocated_bytes'] <= 14*2**30 and sample['evidence_allocated_bytes'] <= 256*2**20
                    for sample in child['samples']), 'actual compiler capacity qualification differs')
            require(not any((receipt.parent/name).exists() for name in ['owned-stop.json', 'budget-reason.json']),
                    'actual compiler underwent a capacity stop')
            for kind in ['stdout', 'stderr']:
                path = frozen(receipt.parent/kind)
                require(path.stat().st_size <= 256*2**20, 'bounded compiler raw stream required')
                raw = path.read_bytes()
                require(digest(raw) == child[kind+'_sha256'], 'actual compiler raw stream differs')
                if kind in wanted:
                    require(raw.decode() == wanted[kind], 'declared compiler probe output differs')
                if failed_support:
                    require(re.search(rb'(?m)^\s*Running `', raw) is None,
                            'failed dispatch unexpectedly contains a Cargo producer')
                    if kind == 'stderr':
                        require(b'ERROR: no `build` rules matched ["src/tools/run-make-support"]\n' in raw,
                                'failed support dispatch reason differs')
                if wanted['argv'][0] == './x':
                    stages = previous_plan['stages'] if root != evidence else plan['stages']
                    require(wanted in stages, 'unproved actual compiler stage')
                    streams[str(path)] = dict(raw=raw, child_receipt=str(receipt), environment=child['environment'],
                        stage_index=stages.index(wanted), history_index=global_index,
                        stream_kind=kind, outer_argv=wanted['argv'], returncode=child['returncode'],
                        failed_support_dispatch=failed_support)
    # Preserve the old fast-probe limitation exactly. Future new fast probes may
    # also exit before lsof: the successor plan must bind their actual list via
    # the independent audit. They are not compiler-producer cwd observations.
    require([i for i in unavailable_cwd if i < 16] == plan['saved']['unavailable_contemporaneous_cwd_children']
            == [0, *range(3, 15)], 'historical cwd limitation was erased or widened')
    require([i-16 for i in unavailable_cwd if 16 <= i < 23]
            == plan['previous_continuation']['unavailable_contemporaneous_cwd_children'] == [1],
            'prior native fast-probe cwd limitation was erased or widened')
    require(not any(row['history_index'] in unavailable_cwd for row in streams.values()),
            'actual compiler producer lacks contemporaneous cwd proof')
    lowering = next(row for row in streams.values() if row['stage_index'] == 1 and row['stream_kind'] == 'stdout')['raw']
    lowering += next(row for row in streams.values() if row['stage_index'] == 1 and row['stream_kind'] == 'stderr')['raw']
    names = re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$', lowering.decode(), re.M)
    require(failed['error'] == repr(AssertionError((names, original['tests']['lowering'])))
            and sorted(names) == sorted(plan['tests']['lowering']['names']) and len(names) == 27,
            'retained failure was not precisely the corrected source-name expectation')
    interface = next(row for row in streams.values() if row['stage_index'] == 6 and row['stream_kind'] == 'stdout')['raw']
    interface += next(row for row in streams.values() if row['stage_index'] == 6 and row['stream_kind'] == 'stderr')['raw']
    names = re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$', interface.decode(), re.M)
    require(sorted(names) == sorted(plan['tests']['interface']['names']) and len(names) == 18,
            'actual complete interface test names differ')
    return dict(plan=plan, original_plan=original, previous_plan=previous_plan, terminal=terminal,
                failed_terminal=failed, failed_support_terminal=middle_failed,
                compiled=compiled, streams=streams, unavailable_contemporaneous_cwd_children=unavailable_cwd)

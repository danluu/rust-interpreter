#!/usr/bin/env python3
"""Measure repeated lowering outputs in unchanged production-edit histories."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_cases import WORKFLOW_VARIANTS
from workflow_io import SourceEdit, capture, require_space, write_json as write
from workflow_measurements import source_states
from bench_e2e_workflow import guest_test_failure
from reuse_check import observation, reconstruction, persistent_cache

REFERENCES = dict(token='fixed-frame-clear-library-token-02', folded='fixed-frame-clear-library-folded-01')


def compare(previous, current, costs=None):
    old = {r['index']: r for r in previous['functions']}
    rows = current['functions']
    weights = {r['index']: r for r in (costs or current)['functions']}
    assert len(weights) == len(rows)
    assert all(all(row[field] == weights[row['index']][field] for field in
                   ['name', 'lowered_sha256', 'final_sha256']) for row in rows)
    def seconds(row, field=None):
        cost = weights[row['index']]
        return cost[field] if field else cost['prepare_seconds'] + cost['lower_seconds']
    same = [r for r in rows if r['index'] in old and r['name'] == old[r['index']]['name']
            and r['lowered_sha256'] == old[r['index']]['lowered_sha256']]
    total = sum(seconds(r) for r in rows)
    repeated = sum(seconds(r) for r in same)
    result = dict(functions=len(rows), repeated_lowered_functions=len(same),
        repeated_final_functions=sum(r['index'] in old and r['name'] == old[r['index']]['name']
            and r['final_sha256'] == old[r['index']]['final_sha256'] for r in rows),
        changed_index_or_name=sum(r['index'] not in old or r['name'] != old[r['index']]['name'] for r in rows),
        observed_function_seconds=total, repeated_output_seconds=repeated,
        repeated_output_cost_fraction=repeated / total if total else 0,
        repeated_prepare_seconds=sum(seconds(r, 'prepare_seconds') for r in same),
        repeated_lower_seconds=sum(seconds(r, 'lower_seconds') for r in same),
        semantics_proven=False)
    if current['schema_version'] >= 2:
        templated = [r for r in rows if r['index'] in old and r['name'] == old[r['index']]['name']
                     and r['typed_template_sha256'] == old[r['index']]['typed_template_sha256']]
        result.update(repeated_typed_templates=len(templated),
            repeated_template_seconds=sum(seconds(r) for r in templated),
            repeated_template_cost_fraction=sum(seconds(r) for r in templated) / total if total else 0,
            pointer_bindings=sum(len(r['relocations']) for r in rows),
            prior_unannotated_weights=costs is not None,
            current_instrumented_function_seconds=sum(r['prepare_seconds'] + r['lower_seconds'] for r in rows))
    if current['schema_version'] == 3:
        old_nodes = {r['dependency']['node']: r for r in previous['functions']}
        green = [r for r in rows if r['dependency']['previous_green']]
        unknown = [r for r in green if r['dependency']['node'] not in old_nodes]
        changed = [r for r in green if r['dependency']['node'] in old_nodes
                   and r['typed_template_sha256'] != old_nodes[r['dependency']['node']]['typed_template_sha256']]
        supported = [r for r in green if r['dependency']['node'] in old_nodes
                     and r['typed_template_sha256'] == old_nodes[r['dependency']['node']]['typed_template_sha256']]
        result.update(green_functions=len(green), unknown_green=len(unknown),
            changed_green_templates=[dict(index=r['index'], name=r['name'], node=r['dependency']['node']) for r in changed],
            supported_green_seconds=sum(seconds(r) for r in supported),
            supported_green_cost_fraction=sum(seconds(r) for r in supported) / total if total else 0,
            green_check_seconds=sum(r['dependency']['green_check_seconds'] for r in rows))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=REFERENCES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--restored-reference-cycle', type=int, choices=[0, 1], required=True,
                        help='preselect the retained original-source artifact from the matching cache history')
    parser.add_argument('--build', type=Path, default=ROOT / 'results/export-reuse-build-01/summary.json')
    parser.add_argument('--qualification', type=Path, default=ROOT / 'results/export-reuse-fixtures-01/summary.json')
    parser.add_argument('--weights-run', type=Path,
                        help='prior unannotated census with identical function outputs; required for typed template costs')
    parser.add_argument('--dependency-qualification', type=Path,
                        help='successful semantic-edit dependency fixture; enables full-recomputation dependency observation')
    parser.add_argument('--cache-qualification', type=Path,
                        help='successful persistent fault controls; enables prior-session verification')
    args = parser.parse_args()
    assert re.fullmatch('export-reuse-' + args.case + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        build_path = args.build.resolve()
        qualification_path = args.qualification.resolve()
        build, qualification = [json.loads(p.read_text()) for p in [build_path, qualification_path]]
        assert build['status'] == qualification['status'] == 'passed'
        typed = qualification.get('typed_relocations', False)
        binding_replay = qualification.get('binding_replay', False)
        assert qualification['commands'] == (231 if binding_replay else 179 if typed else 104) and qualification['all_artifact_hashes_identical']
        assert typed == (args.weights_run is not None)
        assert qualification['tool_key'] == build['tool_key']
        dependencies = args.dependency_qualification is not None
        if dependencies:
            dep_check = json.loads(args.dependency_qualification.read_text())
            assert dep_check['tool_key'] == build['tool_key'] and dep_check['commands'] == 229
            assert dep_check['candidate_dependency_boundary_supported'] and dep_check['all_lowering_executed']
            assert typed
            if binding_replay:
                assert dep_check['binding_replay'] and len(dep_check['reconstruction']) == 9
        assert not binding_replay or dependencies
        cache_verification = args.cache_qualification is not None
        if cache_verification:
            cache_check = json.loads(args.cache_qualification.read_text())
            assert binding_replay and dep_check['persistent_cache']
            assert cache_check['tool_key'] == build['tool_key'] and cache_check['status'] == 'passed'
            assert cache_check['commands'] == 98 and cache_check['failed_publication_after_staging_published_no_session']
        tool, key = installed_tools(build['tool_key'])
        reference_path = ROOT / 'results' / REFERENCES[args.case] / 'summary.json'
        reference = json.loads(reference_path.read_text())
        raw_reference = ROOT / reference['raw'] / 'records.json'
        original_rows = json.loads(raw_reference.read_text())
        references = {r['state']: r for r in original_rows if r['mode'] == 'baseline' and r['cycle'] == 0}
        assert set(references) == {0, -1, 1, 2, 3, 4, 5}
        restored = next(r for r in original_rows if r['mode'] == 'baseline'
                        and r['cycle'] == args.restored_reference_cycle and r['state'] == 0)
        if args.restored_reference_cycle == 1:
            assert restored['previous_source_sha256'] == references[5]['source_sha256']
        assert restored['source_sha256'] == references[0]['source_sha256']
        references['restored'] = restored
        case = WORKFLOW_VARIANTS[reference['project'], reference['workflow']]
        source = ROOT / '.work/sources/fre'
        marker = json.loads((source / '.rust-interp-owned.json').read_text())
        assert marker['owner'] == str(ROOT) and marker['revision'] == reference['revision']
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == marker['revision']
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip()
        path = source / case['file']
        original = path.read_bytes()
        work = ROOT / '.work' / args.run_id
        work.mkdir(exist_ok=False)
        # Exact matching outputs share the already frozen immutable snapshot.
        # A differing output is copied before failure, then the history stops;
        # budget one such full copy, plus the fresh metadata cache and margin.
        inventory = json.loads((ROOT / 'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json').read_text())
        cache_bytes = sum(g['bytes'] for g in inventory['manifest']['groups'])
        max_artifact = max((ROOT / r['artifacts'][0]['path']).stat().st_size for r in references.values())
        # Two finalized generations plus the working generation, each bounded
        # by the exporter's 128 MiB cache limit. Snapshots remain hard-linked.
        function_cache_bytes = 3 * 128 * 1024**2 if cache_verification else 0
        required = 8 * 1024**3 + (cache_bytes + max_artifact + function_cache_bytes) * 12 // 10 + 128 * 1024**2
        free = shutil.disk_usage(ROOT).free
        write(work / 'admission.json', dict(required_free_bytes=required, observed_free_bytes=free,
              prior_custom_cache_bytes=cache_bytes, saved_artifacts=8, max_artifact_bytes=max_artifact,
              maximum_new_snapshot_copies=1, matching_snapshots_share_frozen_reference=True,
              persistent_function_cache_budget_bytes=function_cache_bytes))
        assert free >= required, 'insufficient diagnostic storage; source is unchanged'
        command = list(references[0]['calls'][0]['command'])
        command[1] = str(HERE / 'reuse_launcher.py')
        command[command.index('--tool-key') + 1] = key
        command[command.index('--cache-namespace') + 1] = args.run_id
        paths = [Path(__file__), HERE / 'reuse_launcher.py', HERE / 'reuse_check.py', HERE / 'REUSE.md',
                 build_path, qualification_path, reference_path, raw_reference]
        paths += [ROOT / 'scripts' / p for p in ['interpreter.py', 'workflow_io.py', 'workflow_cases.py', 'workflow_measurements.py', 'std_mir.py']]
        paths += [ROOT / r['artifacts'][0]['path'] for r in references.values()]
        paths += [tool / name for name in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        weights = {}
        if typed:
            paths.append(HERE / 'TYPED-RELOCATIONS.md')
            paths.append(HERE / 'TEMPLATE-WEIGHTS.md')
            prior = args.weights_run.resolve()
            assert prior == ROOT / '.work' / ('export-reuse-' + args.case + '-01')
            weight_rows = json.loads((prior / 'records.json').read_text())
            assert [r['state'] for r in weight_rows] == [0, -1, 1, 2, 3, 4, 5, 'restored']
            paths.extend([prior / 'plan.json', prior / 'records.json'])
            for row in weight_rows:
                census = prior / (str(row['state']) + '.census.json')
                assert sha(census) == row['census_sha256']
                value = json.loads(census.read_text())
                assert value['schema_version'] == 1 and value['artifact_sha256'] == row['artifact_sha256']
                weights[row['state']] = value
                paths.append(census)
        if dependencies:
            paths.extend([args.dependency_qualification.resolve(), HERE / 'DEPENDENCIES.md'])
        if binding_replay:
            paths.append(HERE / 'BINDING-REPLAY.md')
        if cache_verification:
            paths.extend([args.cache_qualification.resolve(), HERE / 'PERSISTENT-REUSE.md'])
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, source_commit=build['source_commit'], tool_key=key,
              source_revision=marker['revision'], command=command, performance_measurement=False,
              restored_reference_cycle=args.restored_reference_cycle,
              weight_source=str(args.weights_run) if typed else 'current unannotated function intervals',
              compiler_dependency_observation=dependencies, all_lowering_executed=True,
              states=[0, -1, 1, 2, 3, 4, 5, 'restored']))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=references[0]['calls'][0]['rustflags'],
                   CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
        if dependencies:
            env['RUST_INTERP_FUNCTION_DEPENDENCIES'] = '1'
        if binding_replay:
            env['RUST_INTERP_BINDING_REPLAY'] = '1'
        if cache_verification:
            env['RUST_INTERP_FUNCTION_CACHE'] = 'verify'
        records, censuses, transitions = [], [], []
        replay_reports = []
        cache_reports = []
        def execute(state):
            require_space(ROOT, 8)
            child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                receipt_path=work / 'active.json', receipt=dict(state=state))
            label = str(state)
            (work / (label + '.stdout')).write_text(stdout)
            (work / (label + '.stderr')).write_text(stderr)
            row = dict(state=state, pid=child.pid, returncode=child.returncode, source_sha256=sha(path))
            records.append(row)
            write(work / 'records.json', records)
            assert (child.returncode == 0) == (state != -1)
            assert guest_test_failure(stderr) if state == -1 else stdout.strip() == '0'
            launches = [json.loads(line.split(': ', 1)[1]) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
            assert len(launches) == 1
            launch = launches[0]
            assert launch['tool_key'] == key and launch['jit_resumable_calls'] and launch['jit_persistent_registers']
            artifact = Path(launch['artifact_path'])
            saved = work / (label + '.rbc')
            expected = references[state]
            digest = sha(artifact)
            frozen_artifact = ROOT / expected['artifacts'][0]['path']
            assert sha(frozen_artifact) == expected['artifacts'][0]['sha256']
            if digest == expected['artifacts'][0]['sha256']:
                os.link(frozen_artifact, saved)
            else:
                shutil.copy2(artifact, saved)
            assert sha(saved) == digest
            row.update(artifact_sha256=sha(saved), artifact=str(saved.relative_to(ROOT)), launch=launch)
            report, scopes = observation(stderr, saved)
            if binding_replay:
                replay_reports.append(dict(state=state, **reconstruction(stderr, report)))
            if cache_verification:
                cached = persistent_cache(stderr, report)
                assert (cached['loaded_entries'] == cached['previous_payload_uses'] == 0) if state == 0 else cached['previous_payload_uses'] > 0
                profile_dir = next(p for p in artifact.parents if p.name == 'debug')
                finalized = {str(p.relative_to(ROOT)): sha(p) for p in profile_dir.glob('incremental/*/s-*/rust-interp-functions-v1.bin')
                             if not p.parent.name.endswith('-working')}
                assert finalized, 'successful Cargo check did not finalize its staged payload'
                write(work / (label + '-finalized-cache-files.json'), finalized)
                cache_reports.append(dict(state=state, **cached))
            assert report['schema_version'] == (3 if dependencies else 2 if typed else 1)
            if dependencies:
                assert len({f['dependency']['node'] for f in report['functions']}) == len(report['functions'])
                if state == 0:
                    assert not any(f['dependency']['previous_green'] for f in report['functions'])
            write(work / (label + '.census.json'), report)
            row.update(census_sha256=sha(work / (label + '.census.json')), timings=scopes)
            row['matches_retained_artifact'] = sha(saved) == expected['artifacts'][0]['sha256']
            write(work / 'records.json', records)
            assert row['source_sha256'] == expected['source_sha256']
            assert row['matches_retained_artifact'], 'artifact differs; preserve evidence and investigate'
            if censuses:
                if typed:
                    assert weights[state]['artifact_sha256'] == report['artifact_sha256']
                transitions.append(dict(before_state=records[-2]['state'], state=state,
                                        **compare(censuses[-1], report, weights.get(state))))
                write(work / 'transitions.json', transitions)
            censuses.append(report)
            assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
            print('PASS', args.case, state, report['observed_functions'], 'functions; original assertions and artifact match', flush=True)
        with SourceEdit(path, original) as edit:
            for state in source_states(original.decode(), case, 1, ['native', 'baseline', 'candidate'], True):
                edit.replace(state['source'])
                execute(state['state'])
        assert path.read_bytes() == original
        execute('restored')
        edited = [r for r in transitions if type(r['state']) is int and r['state'] > 0]
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        result = dict(status='passed', performance_measurement=False, tool_key=key,
              source_commit=build['source_commit'], project=reference['project'], workflow=reference['workflow'],
              revision=reference['revision'], commands=len(records), edited_states=5, wrong_edit_rejected=True,
              source_restored=True, restored_source_rebuilt=True, original_tests_unchanged=True,
              all_artifact_hashes_identical=True, transitions=transitions,
              restored_reference_cycle=args.restored_reference_cycle,
              restored_output_matches_first_anchor=records[-1]['artifact_sha256'] == records[0]['artifact_sha256'],
              median_repeated_output_seconds=statistics.median(r['repeated_output_seconds'] for r in edited),
              median_observed_function_seconds=statistics.median(r['observed_function_seconds'] for r in edited),
              median_repeated_output_cost_fraction=statistics.median(r['repeated_output_cost_fraction'] for r in edited),
              frozen=frozen, raw=str(work.relative_to(ROOT)), records_sha256=sha(work / 'records.json'),
              scope='Cost-weighted repeated outputs only. No semantic cache-key proof, cache hit rate, speedup or cold-build claim.')
        if typed:
            result.update(median_repeated_template_seconds=statistics.median(r['repeated_template_seconds'] for r in edited),
                median_repeated_template_cost_fraction=statistics.median(r['repeated_template_cost_fraction'] for r in edited),
                weight_source=str(args.weights_run),
                weight_scope='Prior unannotated per-function intervals with exact matching outputs. Current pointer-observation cost is excluded from the opportunity estimate; these are not performance samples.')
        if dependencies:
            changed = sum(len(r['changed_green_templates']) for r in transitions)
            unknown = sum(r['unknown_green'] for r in transitions)
            result.update(compiler_dependency_observation=True, all_lowering_executed=True,
                changed_green_templates=changed, unknown_green=unknown,
                candidate_dependency_boundary_supported=changed == unknown == 0 and any(r['green_functions'] for r in transitions),
                median_supported_green_seconds=statistics.median(r['supported_green_seconds'] for r in edited),
                median_supported_green_cost_fraction=statistics.median(r['supported_green_cost_fraction'] for r in edited),
                median_green_check_seconds=statistics.median(r['green_check_seconds'] for r in edited))
        if binding_replay:
            result.update(binding_replay=True, reconstruction=replay_reports,
                replay_scope='Each current function/frame payload is encoded, decoded and bound from current MIR into a second graph. Both complete original lowering and graph verification execute; no persistent cache or performance claim.')
        if cache_verification:
            result.update(persistent_cache=True, prior_payload_verification=cache_reports,
                replay_scope='Green prior-session payloads reconstruct the second graph from current MIR. All original lowering and exact graph verification execute; no skipped lowering or performance claim.')
        write(out / 'summary.json', result)


if __name__ == '__main__':
    main()

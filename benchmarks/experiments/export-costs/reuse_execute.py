#!/usr/bin/env python3
"""Qualify actual skipped lowering through complete production-edit histories."""
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
from reuse_check import actual_cache
from reuse_profile import REFERENCES

BINDINGS = dict(token='export-reuse-token-05', folded='export-reuse-folded-05')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=REFERENCES, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--cache-qualification', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch('export-reuse-execute-' + args.case + r'-\d{2}', args.run_id)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        build_path, qualification_path, cache_path = [p.resolve() for p in [args.build, args.qualification, args.cache_qualification]]
        build, qualification, cache_qualification = [json.loads(p.read_text()) for p in [build_path, qualification_path, cache_path]]
        assert build['status'] == cache_qualification['status'] == 'passed'
        assert len(set(build['tests'].values())) == 1 and min(build['tests'].values()) >= 50
        assert qualification['function_reuse'] and qualification['commands'] == 293
        assert qualification['candidate_dependency_boundary_supported'] and qualification['all_artifact_hashes_identical']
        assert cache_qualification['function_reuse'] and cache_qualification['commands'] == 98
        assert cache_qualification['failed_publication_after_staging_published_no_session']
        assert qualification['tool_key'] == cache_qualification['tool_key'] == build['tool_key']
        tool, key = installed_tools(build['tool_key'])
        reference_path = ROOT / 'results' / REFERENCES[args.case] / 'summary.json'
        reference = json.loads(reference_path.read_text())
        raw_reference = ROOT / reference['raw'] / 'records.json'
        original_rows = json.loads(raw_reference.read_text())
        references = {r['state']: r for r in original_rows if r['mode'] == 'baseline' and r['cycle'] == 0}
        assert set(references) == {0, -1, 1, 2, 3, 4, 5}
        restored = next(r for r in original_rows if r['mode'] == 'baseline' and r['cycle'] == 1 and r['state'] == 0)
        assert restored['previous_source_sha256'] == references[5]['source_sha256']
        assert restored['source_sha256'] == references[0]['source_sha256']
        references['restored'] = restored
        binding_path = ROOT / 'results' / BINDINGS[args.case] / 'summary.json'
        binding = json.loads(binding_path.read_text())
        assert binding['status'] == 'passed' and binding['commands'] == 8 and binding['all_artifact_hashes_identical']
        # The unchanged template schema was measured through these exact edits.
        # Bound the known file size with 64 bytes/index entry and a 20% margin;
        # check the actual staged file against that envelope after each export.
        max_payload = max(r['payload_bytes'] for r in binding['reconstruction'])
        max_entries = max(r['replayed_functions'] for r in binding['reconstruction'])
        cache_envelope = min(128 * 1024**2, (max_payload + 64 * max_entries + 80) * 12 // 10)
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
        inventory = json.loads((ROOT / 'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json').read_text())
        metadata_bytes = sum(g['bytes'] for g in inventory['manifest']['groups'])
        max_artifact = max((ROOT / r['artifacts'][0]['path']).stat().st_size for r in references.values())
        required = 8 * 1024**3 + (metadata_bytes + max_artifact) * 12 // 10 + 3 * cache_envelope + 128 * 1024**2
        free = shutil.disk_usage(ROOT).free
        write(work / 'admission.json', dict(required_free_bytes=required, observed_free_bytes=free,
            prior_custom_metadata_bytes=metadata_bytes, max_artifact_bytes=max_artifact,
            maximum_new_snapshot_copies=1, function_cache_file_envelope=cache_envelope,
            maximum_cache_generations=3, matching_snapshots_share_frozen_reference=True))
        assert free >= required, 'insufficient diagnostic storage; source is unchanged'
        command = list(references[0]['calls'][0]['command'])
        command[1] = str(HERE / 'reuse_execute_launcher.py')
        command[command.index('--tool-key') + 1] = key
        command[command.index('--cache-namespace') + 1] = args.run_id
        paths = [Path(__file__), HERE / 'reuse_execute_launcher.py', HERE / 'reuse_check.py', HERE / 'reuse_profile.py',
            HERE / 'PERSISTENT-REUSE.md', build_path, qualification_path, cache_path, binding_path,
            reference_path, raw_reference, ROOT / 'results/parked-budget-e2e-token-phrase-candidate-archive-01/plan.json']
        paths += [ROOT / 'scripts' / p for p in ['interpreter.py', 'workflow_io.py', 'workflow_cases.py', 'workflow_measurements.py', 'std_mir.py']]
        paths += [ROOT / r['artifacts'][0]['path'] for r in references.values()]
        paths += [tool / n for n in ['rust-interp-mir-export', 'rust-interp-vm', 'rust-interp-rustc-wrapper']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        write(work / 'plan.json', dict(frozen=frozen, source_commit=build['source_commit'], tool_key=key,
            source_revision=marker['revision'], command=command, performance_measurement=False,
            actual_skipped_lowering=True, restored_reference_cycle=1,
            states=[0, -1, 1, 2, 3, 4, 5, 'restored']))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']}
        env.update(RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=references[0]['calls'][0]['rustflags'],
                   CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
        records = []
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
            row.update(artifact_sha256=digest, artifact=str(saved.relative_to(ROOT)), launch=launch)
            row['matches_retained_artifact'] = digest == expected['artifacts'][0]['sha256']
            write(work / 'records.json', records)
            assert row['source_sha256'] == expected['source_sha256']
            assert row['matches_retained_artifact'], 'artifact differs; preserve evidence and investigate'
            cached = actual_cache(stderr)
            assert cached['skipped_functions'] == 0 if state == 0 else cached['skipped_functions'] > 0
            assert cached['staged_bytes'] <= cache_envelope
            profile_dir = next(p for p in artifact.parents if p.name == 'debug')
            finalized = {str(p.relative_to(ROOT)): sha(p) for p in profile_dir.glob('incremental/*/s-*/rust-interp-functions-v1.bin')
                         if not p.parent.name.endswith('-working')}
            assert finalized
            write(work / (label + '-finalized-cache-files.json'), finalized)
            row['cache'] = cached
            write(work / 'records.json', records)
            assert all(sha(ROOT / p) == digest for p, digest in frozen.items())
            print('PASS', args.case, state, cached['skipped_functions'], 'skipped;', cached['lowered_functions'], 'lowered; original assertions and bytecode', flush=True)
        with SourceEdit(path, original) as edit:
            for state in source_states(original.decode(), case, 1, ['native', 'baseline', 'candidate'], True):
                edit.replace(state['source'])
                execute(state['state'])
        assert path.read_bytes() == original
        execute('restored')
        edited = [r for r in records if type(r['state']) is int and r['state'] > 0]
        result = dict(status='passed', performance_measurement=False, tool_key=key,
            source_commit=build['source_commit'], project=reference['project'], workflow=reference['workflow'],
            revision=reference['revision'], commands=len(records), edited_states=5, wrong_edit_rejected=True,
            source_restored=True, restored_source_rebuilt=True, original_tests_unchanged=True,
            all_artifact_hashes_identical=True, actual_skipped_lowering=True,
            cache_reports=[dict(state=r['state'], **r['cache']) for r in records],
            median_edited_cache_seconds={k: statistics.median(r['cache'][k] for r in edited)
                for k in edited[0]['cache'] if k.endswith('_seconds')},
            frozen=frozen, raw=str(work.relative_to(ROOT)), records_sha256=sha(work / 'records.json'),
            scope='Actual reuse correctness and cost attribution. No paired native/control timing, performance gate or speedup claim.')
        out = ROOT / 'results' / args.run_id
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', result)


if __name__ == '__main__':
    main()

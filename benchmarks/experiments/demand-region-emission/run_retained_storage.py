"""Inventory retained analysis payload for exact saved Rust program graphs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
NAME = 'demand-analysis-storage-03'
ARTIFACTS = {
    'token': ('.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc',
              'caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9'),
    'folded': ('.work/call-capacity-credit-edit-folded-01/artifacts/2a869f1607f67f6878809b51705203f573fb0f38cb1a325f41c09597315b666c.rbc',
               '2a869f1607f67f6878809b51705203f573fb0f38cb1a325f41c09597315b666c'),
    'parser': ('.work/guarded-local-facts-main-parser-01/artifact.rbc',
               'a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61'),
}


def read(p):
    return json.loads(p.read_text())


def aggregate(rows):
    assert rows
    fields = {k: sum(r['fields'][k] for r in rows) for k in rows[0]['fields']}
    total = sum(r['vector_box_and_inline_bytes'] for r in rows)
    assert sum(fields.values()) == total
    return dict(functions=len(rows), fields=fields, vector_box_and_inline_bytes=total,
        map_entry_tuple_bytes=sum(r['map_entry_tuple_bytes'] for r in rows),
        fill_hint_entries=sum(r['fill_hint_entries'] for r in rows),
        call_slot_hint_entries=sum(r['call_slot_hint_entries'] for r in rows),
        fill_map_entries=sum(r['fill_map_entries'] for r in rows),
        call_slot_map_entries=sum(r['call_slot_map_entries'] for r in rows),
        excluded_test_only_liveness_buffer_bytes=sum(r.get('excluded_test_only_liveness_buffer_bytes',0) for r in rows),
        pcs=sum(r['pcs'] for r in rows), regions=sum(r['regions'] for r in rows),
        guarded_regions=sum(r['guarded_regions'] for r in rows),
        top_functions=sorted(rows, key=lambda r: r['vector_box_and_inline_bytes'], reverse=True)[:8])


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        frozen = {}
        def bind(path, expected=None):
            path = Path(path); h = sha(path)
            if expected is not None: assert h == expected, str(path)
            frozen[str(path.relative_to(ROOT))] = h
            return read(path) if path.suffix == '.json' else h
        for path, h in ARTIFACTS.values(): bind(ROOT / path, h)
        path = ROOT / 'results/scratch-memory-values-profile-01/closure.json'
        closure = bind(path); assert closure['status'] == 'closed' and closure['all_hashes_verified']
        summary = bind(path.with_name('summary.json'), closure['summary_sha256'])
        assert summary['status'] == 'passed' and summary['exact_operation_map_reconstruction']
        bindings = bind(ROOT / closure['bindings'], closure['bindings_sha256'])
        maps = {}
        for label, row in zip(['block', 'exhaustive', 'folded'], [r for r in summary['comparisons'] if r['mode']=='candidate']):
            path = (ROOT / row['code_path']).with_name('map.json')
            assert bindings['artifacts'][str(path.relative_to(ROOT))] == row['map_sha256']
            maps[label] = bind(path, row['map_sha256'])
        for path in Path(__file__).parent.iterdir():
            if path.suffix in ['.py', '.md']: bind(path)
        for path in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines():
            bind(ROOT / path)
        for path in ['compare_saved_runtime.py', 'workflow_io.py']: bind(ROOT / 'scripts' / path)
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME; work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
            target=str(target.relative_to(ROOT)), same_source_root=True, required_free_bytes=needed,
            allocated_target_bytes=allocated, minimum_child_gib=8, expected_commands=5,
            guest_commands=0, executable_code_publications=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'STORAGE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', RUST_TEST_THREADS='2')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--release', '--lib', '-p', 'rust-interp-bytecode',
                 '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(target)]
        prefix = 'jit::function_analysis::storage::'
        commands = [('debug', [x for x in cargo if x != '--release'] + [prefix], {}, 1),
                    ('release', cargo + [prefix], {}, 1)]
        for label, (path, h) in ARTIFACTS.items():
            commands.append((label, cargo + [prefix + 'observe_saved_analysis_storage', '--', '--ignored', '--exact'],
                dict(STORAGE_ARTIFACT=str(ROOT / path), STORAGE_OUTPUT=str(work / (label + '.json'))), 0))
        records = []
        for label, command, extra, ignored in commands:
            require_space(ROOT, 8)
            assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            start = time.time()
            child, out, err = capture(command, cwd=ROOT, env=env | extra,
                receipt_path=work / 'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]: (work / (label + '.' + stream)).write_text(payload)
            records.append(dict(label=label, command=command, extra_env=extra, pid=child.pid,
                returncode=child.returncode, seconds=time.time() - start,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            assert f'test result: ok. 1 passed; 0 failed; {ignored} ignored;' in out
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        cases = []; details = {}
        for label, (path, h) in ARTIFACTS.items():
            detail = read(work / (label + '.json'))
            assert detail['status'] == 'passed' and detail['artifact_sha256'] == h
            assert detail['guest_commands'] == detail['executable_code_publications'] == 0
            rows = detail['functions']; assert [r['id'] for r in rows] == list(range(len(rows)))
            details[label] = rows
            cases.append(dict(case=label, all_validated_functions=aggregate(rows),
                detail_sha256=sha(work / (label + '.json'))))
        selected = []
        for label, mapping in maps.items():
            rows = details['folded' if label == 'folded' else 'token']
            ordinary_by_id = {}
            for region in mapping['ranges']:
                if region['kind'] == 'scalar_leaf': continue
                assert region['kind'] in ['resumable_region', 'resumable_call', 'resumable_return']
                old = ordinary_by_id.setdefault(region['function'], region)
                assert old['name'] == region['name']
            ordinary = [ordinary_by_id[i] for i in sorted(ordinary_by_id)]
            chosen = [rows[f['function']] for f in ordinary]
            assert len({r['id'] for r in chosen}) == len(chosen)
            assert all(r['name'] == f['name'] for r, f in zip(chosen, ordinary))
            selected.append(dict(case=label, captured_ordinary_functions=aggregate(chosen)))
        out = ROOT / 'results' / NAME; out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', commands=5, controls_per_profile=1,
            source_revision=revision, raw=str(work.relative_to(ROOT)), plan_sha256=sha(work / 'plan.json'),
            records_sha256=sha(work / 'records.json'), cases=cases, captured_subsets=selected,
            setup_seconds=sum(r['seconds'] for r in records), guest_commands=0,
            executable_code_publications=0, production_runtime_changes=1, performance_measurement=False,
            scope=detail['scope']))


if __name__ == '__main__':
    main()

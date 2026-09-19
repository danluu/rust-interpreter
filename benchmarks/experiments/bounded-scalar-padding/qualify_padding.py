"""Qualify layout-bounded scalar commit stores in the owned runtime target."""
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'benchmarks/experiments/short-clear-tails'))
import qualify as bounded_build

focus = bounded_build.focus
read, sha, write = bounded_build.read, bounded_build.sha, bounded_build.write
admission, TARGET, BUILD = bounded_build.admission, bounded_build.TARGET, bounded_build.BUILD
RUN = 'bounded-scalar-padding-focused-01'
BASE = '52d13ae7'
NAMES = ['jit::scalar_calls::tests::' + name for name in [
    'bounded_padding_native_stores_preserve_exact_bytes_cursor_and_live_registers',
    'bounded_padding_scalar_commits_clear_dirty_retained_histories_and_preserve_limits',
    'native_scalar_call_matches_complete_vm_aliases_profiles_and_peak_memory',
    'native_scalar_call_resource_tails_and_original_error_order_match',
    'native_scalar_call_new_frame_arguments_and_result_padding_fall_back',
    'native_scalar_call_preserves_escaped_addresses_and_future_zeroing',
    'native_scalar_call_private_failures_and_full_width_switches_replay_original_errors',
    'native_scalar_call_heap_pointer_boundaries_and_large_caller_registers_match',
    'native_scalar_call_shared_arena_maps_and_prepared_option_identity_are_exact',
    'native_scalar_call_commits_every_profile_word_and_exact_budget_boundary',
    'native_scalar_call_all_capture_widths_keep_aliases_high_lanes_and_empty_inputs',
    'native_scalar_call_zero_results_preserve_fixed_variable_and_fault_budget_paths']]
NAMES += [n for n in bounded_build.NAMES if not n.endswith('short_clear_tails_preserve_exact_cursor_and_live_registers')]
NAMES += ['jit::code_spans::protocol_census::' + n for n in [
    'protocol_partitions_cover_copy_sizes_profiles_and_register_clearing',
    'protocol_partition_rejects_gaps_overlaps_missing_tail_and_argument_aliases',
    'scalar_protocol_partitions_preserve_complete_native_and_fallback_links']]
assert len(NAMES) == len(set(NAMES)) == 21


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        bounded_build.acquire_lock(lock, 45)
        admission()
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        changed = subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'crates'], cwd=ROOT, text=True).splitlines()
        assert changed == ['crates/bytecode/src/jit/' + p for p in
                           ['code_spans/protocol_census.rs', 'resumable.rs', 'scalar_calls.rs', 'scalar_calls/tests.rs']]
        prior = ROOT / 'results/bounded-scalar-padding-scope-02'
        closed, scope = read(prior / 'closure.json'), read(prior / 'summary.json')
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        assert closed['summary_sha256'] == sha(prior / 'summary.json')
        assert closed['terminal_sha256'] == sha(prior / 'terminal.json')
        assert read(prior / 'terminal.json')['returncode'] == 0 and scope['status'] == 'passed'
        assert [c['padding_samples'] for c in scope['comparisons']] == [14, 37, 18, 12]
        owner = read(BUILD / 'owner.json')
        assert owner['owner'] == str(ROOT) and owner['target'] == str(TARGET)
        paths = [ROOT / p for p in subprocess.check_output(
            ['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], cwd=ROOT, text=True).splitlines()]
        paths += [*HERE.glob('*.py'), *HERE.glob('*.md'), Path(focus.__file__), Path(bounded_build.__file__), BUILD / 'owner.json']
        paths += [ROOT / 'scripts' / p for p in ['workflow_io.py', 'workflow_measurements.py', 'compare_saved_runtime.py', 'supervise_experiment.py']]
        paths += [prior / p for p in ['closure.json', 'summary.json', 'terminal.json']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        raw = ROOT / '.work' / RUN
        raw.mkdir(exist_ok=False)
        write(raw / 'records.json', [])
        write(raw / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
              controller_command=[sys.executable, *sys.orig_argv[1:]], expected_commands=2,
              target=str(TARGET), target_purpose='bounded scalar padding native and VM correctness fixtures',
              runtime_diff_files=changed, tests=NAMES, original_project_guest_commands=0,
              native_fixture_execution=True, performance_measurement=False, default_runtime_adoption=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_')) and k not in
               ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS', 'PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', RUST_TEST_THREADS='2', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        records = []
        for label, extra in [('debug', []), ('release', ['--release'])]:
            current = admission()
            command = ['cargo', '+nightly-2026-09-08', 'test', *extra, '--locked', '--offline', '--jobs', '2',
                       '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(TARGET),
                       '-p', 'rust-interp-bytecode', '--lib', '--', '--exact', '--test-threads=2', *NAMES]
            usage, start = bounded_build.child_usage(), time.perf_counter()
            child, out, err = bounded_build.capture(command, cwd=ROOT, env=env,
                receipt_path=raw / (label + '-child.json'), receipt=dict(label=label))
            seconds, cpu = time.perf_counter() - start, bounded_build.child_cpu_since(usage)
            for stream, value in [('stdout', out), ('stderr', err)]:
                (raw / (label + '.' + stream)).write_text(value)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                seconds=seconds, cpu=cpu, admission=current, stdout_sha256=sha(raw / (label + '.stdout')),
                stderr_sha256=sha(raw / (label + '.stderr')),
                outputs={str((raw / (label + '-child.json')).relative_to(ROOT)): sha(raw / (label + '-child.json'))}))
            write(raw / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            assert 'test result: ok. 21 passed; 0 failed; 0 ignored;' in out
            assert all(name + ' ... ok' in out for name in NAMES)
            records[-1]['after'] = admission()
            write(raw / 'records.json', records)
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, '21 exact scalar/padding/protocol controls passed', flush=True)
        result = ROOT / 'results' / RUN
        result.mkdir(exist_ok=False)
        write(result / 'summary.json', dict(status='passed', source_revision=revision, raw=str(raw.relative_to(ROOT)),
              plan_sha256=sha(raw / 'plan.json'), records_sha256=sha(raw / 'records.json'), commands=2,
              tests_per_profile=21, setup_seconds=sum(r['seconds'] for r in records),
              setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),
              original_project_guest_commands=0, native_fixture_execution=True,
              performance_measurement=False, default_runtime_adoption=False))


def close():
    raw = ROOT / '.work' / RUN
    terminal = read(ROOT / '.work/experiments' / RUN / 'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        records = read(raw / 'records.json')
        assert len(records) == 2
        for row in records:
            child = read(raw / (row['label'] + '-child.json'))
            assert child['status'] == 'finished' and child['returncode'] == row['returncode'] == 0
            assert child['pid'] == row['pid'] and child['parent_pid'] == terminal['child_pid']
            assert child['command'] == row['command']
            out = (raw / (row['label'] + '.stdout')).read_text()
            assert 'test result: ok. 21 passed; 0 failed; 0 ignored;' in out
            assert all(name + ' ... ok' in out for name in NAMES)
            for receipt in [row['admission'], row['after']]:
                assert receipt['allocated_target_bytes'] <= 3 * 1024**3
                assert receipt['required_free_bytes'] == max(14 * 1024**3, 8 * 1024**3 + 2 * receipt['allocated_target_bytes'])
                assert receipt['free_bytes'] >= receipt['required_free_bytes']
    focus.RUN = RUN
    focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:
        close()
    else:
        assert len(sys.argv) == 1
        main()

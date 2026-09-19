"""Qualify exact short tails in a fresh bounded runtime-only target."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
read = focus.read
RUN = 'short-clear-tail-focused-01'
BASE = 'fca687ebac0ea9374a1426addd01169fe707f608'
BUILD = ROOT/'.work/short-clear-tail-runtime-build-01'
TARGET = BUILD/'target'
NAMES = ['jit::resumable::tests::'+name for name in [
    'fixed_zeroing_matches_every_dirty_extent_and_unaligned_start',
    'call_frame_clear_matches_actual_padding_and_preserves_live_call_registers',
    'fixed_clear_layout_requires_an_already_aligned_extent',
    'fixed_clear_proof_survives_retained_alignment_history',
    'reused_guest_frames_clear_padding_and_preserve_limits',
    'bulk_zeroing_matches_exact_dirty_ranges_and_preserves_spare_bytes',
    'short_clear_tails_preserve_exact_cursor_and_live_registers']]


def admission():
    allocated = int(subprocess.check_output(['du','-sk',str(TARGET)],text=True).split()[0])*1024 if TARGET.exists() else 0
    needed = max(14*1024**3,8*1024**3+2*allocated)
    free = shutil.disk_usage(ROOT).free
    assert allocated <= 3*1024**3,('target exceeded declared cap',allocated)
    assert free >= needed,(free,needed)
    return dict(allocated_target_bytes=allocated,required_free_bytes=needed,free_bytes=free)


def main():
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    diff = subprocess.check_output(['git','diff','--name-only',BASE,'--','crates'],cwd=ROOT,text=True).splitlines()
    assert diff == ['crates/bytecode/src/jit/native_calls.rs','crates/bytecode/src/jit/resumable_tests.rs']
    prior = ROOT/'results/short-clear-tail-scope-01'
    closure,proof = read(prior/'closure.json'),read(prior/'summary.json')
    assert closure['status'] == 'closed' and closure['all_hashes_verified']
    assert sha(prior/'summary.json') == closure['summary_sha256'] and sha(prior/'terminal.json') == closure['terminal_sha256']
    assert proof['status'] == 'passed' and proof['assembler_words_match'] and proof['controls']['canary_cases'] == 1024
    assert [r['samples']['byte_tail'] for r in proof['scopes']] == [39,52,66,39]
    paths = [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
    paths += [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__)]
    paths += [ROOT/'scripts'/p for p in ['workflow_io.py','workflow_measurements.py','compare_saved_runtime.py','supervise_experiment.py']]
    paths += [prior/p for p in ['closure.json','summary.json','terminal.json']]
    paths += [ROOT/proof['raw']/p for p in ['plan.json','records.json','controls.json','tail.s','tail.o','scopes.json']]
    frozen = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
    write(raw/'records.json',[])
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=2,target=str(TARGET.relative_to(ROOT)),
        build_owner=str(BUILD.relative_to(ROOT)),maximum_target_allocated_bytes=3*1024**3,
        minimum_initial_gib=14,minimum_child_gib=8,adopted_runtime_source=BASE,runtime_diff_files=diff,
        tests=NAMES,original_project_guest_commands=0,native_fixture_execution=True,
        performance_measurement=False,default_runtime_adoption=False))
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        assert not BUILD.exists()
        initial = admission()
        BUILD.mkdir();TARGET.mkdir()
        owner = dict(owner=str(ROOT),run_id=RUN,source_revision=revision,target=str(TARGET),initial_admission=initial,
            maximum_target_allocated_bytes=3*1024**3,purpose='runtime-only short-clear-tail qualification')
        write(BUILD/'owner.json',owner)
        write(raw/'build-owner.json',owner)
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        records = []
        for label,extra in [('debug',[]),('release',['--release'])]:
            current = admission();require_space(ROOT,8)
            command = ['cargo','+nightly-2026-09-08','test',*extra,'--locked','--offline','--jobs','2',
                '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-bytecode',
                '--lib','--','--exact','--test-threads=2',*NAMES]
            usage,start = child_usage(),time.perf_counter()
            child,out,err = capture(command,cwd=ROOT,env=env,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
            elapsed,cpu = time.perf_counter()-start,child_cpu_since(usage)
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                seconds=elapsed,cpu=cpu,admission=current,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode == 0,(out+err)[-6000:]
            assert 'test result: ok. 7 passed; 0 failed; 0 ignored;' in out
            assert all('test '+name+' ... ok' in out for name in NAMES)
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            records[-1]['after'] = admission();write(raw/'records.json',records)
            print(label,'seven native clear/canary/register/limit controls passed',flush=True)
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        outputs = {str((raw/'build-owner.json').relative_to(ROOT)):sha(raw/'build-owner.json'),
            str((BUILD/'owner.json').relative_to(ROOT)):sha(BUILD/'owner.json')}
        for label in ['debug','release']:
            outputs[str((raw/(label+'-child.json')).relative_to(ROOT))] = sha(raw/(label+'-child.json'))
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=2,
            tests_per_profile=7,setup_seconds=sum(r['seconds'] for r in records),
            setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),adopted_runtime_source=BASE,
            runtime_diff_files=diff,target=str(TARGET.relative_to(ROOT)),final_admission=admission(),outputs=outputs,
            original_project_guest_commands=0,native_fixture_execution=True,
            performance_measurement=False,default_runtime_adoption=False))


def close():
    raw = ROOT/'.work'/RUN
    terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,records,summary = read(raw/'plan.json'),read(raw/'records.json'),read(ROOT/'results'/RUN/'summary.json')
        assert summary['tests_per_profile'] == 7 and summary['commands'] == len(records) == 2
        assert read(BUILD/'owner.json') == read(raw/'build-owner.json')
        for row in records:
            out = (raw/(row['label']+'.stdout')).read_text()
            assert 'test result: ok. 7 passed; 0 failed; 0 ignored;' in out
            assert all('test '+name+' ... ok' in out for name in NAMES)
            for receipt in [row['admission'],row['after']]:
                allocated = receipt['allocated_target_bytes']
                assert allocated <= plan['maximum_target_allocated_bytes']
                assert receipt['required_free_bytes'] == max(14*1024**3,8*1024**3+2*allocated)
                assert receipt['free_bytes'] >= receipt['required_free_bytes']
        assert summary['setup_seconds'] == sum(r['seconds'] for r in records)
        assert summary['setup_cpu_seconds'] == sum(r['cpu']['total_seconds'] for r in records)
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']: close()
    else:
        assert len(sys.argv) == 1
        main()

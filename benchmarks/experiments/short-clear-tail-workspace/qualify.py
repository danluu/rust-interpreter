"""Full verification of the bounded short-clear-tail runtime candidate."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/short-clear-tails'))
from qualify import admission,TARGET,BUILD,BASE
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
read = focus.read
RUN = 'short-clear-tail-workspace-01'


def main():
    focused = ROOT/'results/short-clear-tail-focused-01'
    closure,proof = read(focused/'closure.json'),read(focused/'summary.json')
    assert closure['status'] == 'closed' and closure['all_hashes_verified']
    assert sha(focused/'summary.json') == closure['summary_sha256'] and sha(focused/'terminal.json') == closure['terminal_sha256']
    assert proof['status'] == 'passed' and proof['tests_per_profile'] == 7 and proof['commands'] == 2
    old = ROOT/proof['raw']
    assert sha(old/'plan.json') == proof['plan_sha256']
    assert read(BUILD/'owner.json') == read(old/'build-owner.json')
    assert read(BUILD/'owner.json')['owner'] == str(ROOT)
    for p,h in read(old/'plan.json')['frozen'].items():
        assert sha(ROOT/p) == h,p
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    diff = subprocess.check_output(['git','diff','--name-only',BASE,'--','crates'],cwd=ROOT,text=True).splitlines()
    assert diff == proof['runtime_diff_files']
    paths = [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','scripts','tests','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
    paths += [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__),
        ROOT/'benchmarks/experiments/short-clear-tails/qualify.py',BUILD/'owner.json']
    paths += [focused/p for p in ['summary.json','closure.json','terminal.json']]
    paths += [old/p for p in ['plan.json','records.json','build-owner.json']]
    frozen = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
    write(raw/'records.json',[])
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=4,
        target=str(TARGET.relative_to(ROOT)),maximum_target_allocated_bytes=3*1024**3,minimum_child_gib=8,
        adopted_runtime_source=BASE,runtime_diff_files=diff,original_project_guest_commands=0,
        native_fixture_execution=True,performance_measurement=False,default_runtime_adoption=False))
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);admission()
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common = ['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(TARGET)]
        commands = [('python',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v']),
            ('debug',['cargo','+nightly-2026-09-08','test',*common,'--workspace']),
            ('release',['cargo','+nightly-2026-09-08','test','--release',*common,'--workspace']),
            ('vm',['cargo','+nightly-2026-09-08','build','--release',*common,'-p','rust-interp-bytecode','--bin','rust-interp-vm'])]
        records,totals,outputs = [],{},{}
        for label,command in commands:
            current = admission();require_space(ROOT,8)
            usage,start = child_usage(),time.perf_counter()
            child,out,err = capture(command,cwd=ROOT,env=env,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
            elapsed,cpu = time.perf_counter()-start,child_cpu_since(usage)
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                seconds=elapsed,cpu=cpu,admission=current,
                stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))))
            write(raw/'records.json',records)
            assert child.returncode == 0,(out+err)[-6000:]
            if label == 'python':
                count, = re.findall(r'Ran (\d+) tests? in ',err)
                skipped, = re.findall(r'^OK(?: \(skipped=(\d+)\))?$',err,re.M)
                assert int(count) == 468 and int(skipped or 0) == 22
                totals[label] = dict(discovered=468,passed=446,skipped=22)
            elif label in ['debug','release']:
                cases = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
                assert cases and all(int(failed) == 0 for _,failed,_ in cases)
                totals[label] = dict(passed=sum(int(p) for p,_,_ in cases),ignored=sum(int(i) for _,_,i in cases))
                assert totals[label] == dict(passed=615,ignored=13),totals[label]
                for name in ['short_clear_tails_preserve_exact_cursor_and_live_registers',
                    'scratch_memory_overlapping_reused_copy_invalidates_its_original_source',
                    'native_scalar_2187_copy_cases_in_both_profile_modes',
                    'native_scalar_call_commits_every_profile_word_and_exact_budget_boundary']:
                    assert name+' ... ok' in out,name
            else:
                snapshot = raw/'rust-interp-vm'
                shutil.copy2(TARGET/'release/rust-interp-vm',snapshot)
                outputs[str(snapshot.relative_to(ROOT))] = sha(snapshot)
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            records[-1]['after'] = admission();write(raw/'records.json',records)
            outputs[str((raw/(label+'-child.json')).relative_to(ROOT))] = sha(raw/(label+'-child.json'))
            print(label,'passed',totals.get(label),flush=True)
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=4,
            tests=totals,setup_seconds=sum(r['seconds'] for r in records),
            setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),adopted_runtime_source=BASE,
            runtime_diff_files=diff,target=str(TARGET.relative_to(ROOT)),final_admission=admission(),outputs=outputs,
            original_project_guest_commands=0,native_fixture_execution=True,
            performance_measurement=False,default_runtime_adoption=False))


def close():
    raw = ROOT/'.work'/RUN
    terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        summary,records = read(ROOT/'results'/RUN/'summary.json'),read(raw/'records.json')
        assert summary['commands'] == len(records) == 4
        assert summary['tests'] == dict(python=dict(discovered=468,passed=446,skipped=22),
            debug=dict(passed=615,ignored=13),release=dict(passed=615,ignored=13))
        for row in records:
            text = (raw/(row['label']+'.stdout')).read_text()
            if row['label'] in ['debug','release']:
                counts = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',text)
                assert sum(int(p) for p,_,_ in counts) == 615 and sum(int(i) for _,_,i in counts) == 13
                assert all(int(f) == 0 for _,f,_ in counts)
            for receipt in [row['admission'],row['after']]:
                allocated = receipt['allocated_target_bytes']
                assert allocated <= 3*1024**3
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

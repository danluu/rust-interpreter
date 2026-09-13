"""Qualify the combined main exporter without changing performance evidence."""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write


def main():
    run = 'reuse-misses-main-qualification-01'
    work = ROOT / '.work' / run
    build_path = ROOT / 'results/reuse-misses-main-build-01/summary.json'
    build = json.loads(build_path.read_text())
    assert build['status'] == 'passed' and build['tests'] == {'test-debug':88, 'test-release':88}
    tools, key = installed_tools(build['tool_key'])
    source = ROOT / build['source_manifest']
    assert sha(source) == build['source_manifest_sha256']
    assert all(sha(ROOT / p) == h for p,h in json.loads(source.read_text())['frozen'].items())
    env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
           and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                         'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','CARGO_BUILD_BUILD_DIR','RUST_TEST_THREADS']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(PYTHONDONTWRITEBYTECODE='1', CARGO_TERM_COLOR='never')
    files = list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'tests').glob('*.py'))
    files += [p for d in ['reuse-misses','reuse-misses-main'] for p in (ROOT / 'benchmarks/experiments' / d).glob('*') if p.is_file()]
    files += [build_path, source] + [tools / name for name in build['binaries']]
    frozen = {str(p.relative_to(ROOT)):sha(p) for p in files}
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,16)
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen, performance_measurement=False,
             expected_python_tests=[14,56,10], observer_commands=44))
        rows = []

        def run_command(label, command, cwd, child_env):
            require_space(ROOT,8)
            child,out,err = capture(command,cwd=cwd,env=child_env,receipt_path=work / 'active.json',receipt=dict(stage=label))
            (work / (label+'.stdout')).write_text(out);(work / (label+'.stderr')).write_text(err)
            row = dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                       stdout_sha256=sha(work / (label+'.stdout')),stderr_sha256=sha(work / (label+'.stderr')))
            rows.append(row);write(work / 'records.json',rows)
            assert child.returncode == 0, err[-8000:]
            return out,err

        tests = [
            ('observer-harness',14,ROOT,['discover','-s',str(ROOT/'benchmarks/experiments/reuse-misses'),'-p','test_*.py'],env),
            ('launcher',56,ROOT/'tests',['-v','test_borrowck_cache_launcher','test_interpreter_build_metrics',
                'test_workspace_cache','test_isolated_launcher','test_cargo_targets','test_test_discovery','test_toolchain_lookup'],env),
            ('compiler-cargo',10,ROOT/'tests',['-v','test_borrowck_cache','test_borrowck_cache_cargo'],dict(env,
                RUST_INTERP_TEST_EXPORTER=str(tools/'rust-interp-mir-export'),
                RUST_INTERP_TEST_VM=str(tools/'rust-interp-vm'),RUST_INTERP_TEST_ARTIFACT_DIR=str(work/'fixtures'))),
        ]
        for label,count,cwd,args,child_env in tests:
            _,err = run_command(label,[sys.executable,'-m','unittest',*args],cwd,child_env)
            assert re.search(r'Ran '+str(count)+r' tests in',err) and not re.search(r'skipped=\d',err),err
            rows[-1]['passed_tests']=count;write(work/'records.json',rows)
            print(label,'passed',count,flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
    # Each project child holds the same lock for its entire history.
    directory = ROOT/'benchmarks/experiments/reuse-misses'
    for label,script,name,extra,expected in [
        ('fixture','qualify.py','reuse-misses-fixture-03',[],28),
        ('token','project.py','reuse-misses-token-02',['--qualification','results/reuse-misses-fixture-03/summary.json'],16),
    ]:
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        command=[sys.executable,str(directory/script),'--run-id',name,'--build',str(build_path),
                 '--expected-exporter-tests','88',*extra]
        run_command(label,command,ROOT,env)
        path=ROOT/'results'/name/'summary.json';proof=json.loads(path.read_text())
        assert proof['status']=='passed' and proof['commands']==expected and proof['tool_key']==key
        rows[-1]['summary_sha256']=sha(path);write(work/'records.json',rows)
        print(label,'passed',flush=True)
    assert all(sha(ROOT/p)==h for p,h in frozen.items())
    assert all(sha(ROOT/p)==h for p,h in json.loads(source.read_text())['frozen'].items())
    command_files=list((work/'fixtures').rglob('commands.jsonl'))
    compiler_commands=sum(len(p.read_text().splitlines()) for p in command_files)
    destination=ROOT/'results'/run;destination.mkdir(exist_ok=False)
    write(destination/'summary.json',dict(status='passed',tool_key=key,source_commit=build['source_commit'],
          exporter_tests_per_profile=88,python_tests=80,observer_commands=44,compiler_fixture_commands=compiler_commands,
          performance_measurement=False,raw=str(work.relative_to(ROOT)),
          plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
          compiler_command_files={str(p.relative_to(ROOT)):sha(p) for p in command_files}))


if __name__ == '__main__':
    main()

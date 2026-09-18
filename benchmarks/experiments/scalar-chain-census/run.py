"""Measure initialized/confined small direct-call DAG scope against closed samples."""
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
NAME = 'scalar-chain-census-03'


def read(p):
    return json.loads(p.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        allocated = int(subprocess.check_output(['du', '-sk', str(target)], text=True).split()[0]) * 1024
        needed = max(14 * 1024**3, 8 * 1024**3 + 2 * allocated)
        assert shutil.disk_usage(ROOT).free >= needed, 'insufficient conservative build admission'
        paths=[];historical={}
        for run in ['scratch-scalar-runtime-sampling-01','parser-runtime-sampling-02']:
            closed_path=ROOT/'results'/run/'closure.json';summary_path=closed_path.with_name('summary.json')
            closed,summary=read(closed_path),read(summary_path)
            assert closed['status']=='closed' and closed['all_hashes_verified']
            assert summary['status']=='passed' and sha(summary_path)==closed['summary_sha256']
            bindings_path=ROOT/closed['artifact_bindings'];assert sha(bindings_path)==closed['artifact_bindings_sha256']
            paths += [closed_path,summary_path,bindings_path]
            for p,h in read(bindings_path).items():
                if p.startswith(('.work/','results/')):assert sha(ROOT/p)==h
                else:
                    data=subprocess.check_output(['git','show',closed['source_revision']+':'+p]);assert hashlib.sha256(data).hexdigest()==h
                    historical[run+':'+p]=dict(path=p,revision=closed['source_revision'],sha256=h)
                paths.append(ROOT/p)
        prior=ROOT/'results/current-call-shapes-01'
        prior_closed=read(prior/'closure.json');prior_summary=read(prior/'summary.json')
        assert prior_closed['status']=='closed' and prior_closed['all_hashes_verified']
        assert prior_summary['status']=='passed' and sha(prior/'summary.json')==prior_closed['summary_sha256']
        prior_binding=ROOT/prior_closed['bindings'];assert sha(prior_binding)==prior_closed['bindings_sha256']
        for p,h in read(prior_binding)['artifacts'].items():
            assert sha(ROOT/p)==h;paths.append(ROOT/p)
        paths += [prior_binding,*[prior/n for n in ['summary.json','closure.json','attribution.json']]]
        paths += [ROOT/'benchmarks/experiments/native-call-cost-census'/n for n in ['analyze.py','test_analyze.py']]
        paths += [p for p in Path(__file__).parent.iterdir() if p.suffix in ['.py', '.md']]
        paths += [ROOT / p for p in subprocess.check_output(['git', 'ls-files', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'], text=True).splitlines()]
        paths += [ROOT / 'scripts' / p for p in ['compare_saved_runtime.py', 'workflow_io.py', 'summarize_owned_sample.py']]
        artifact = ROOT / '.work/call-capacity-credit-edit-token-02/artifacts/caa66fcf85d85196264fd2fc5b024918f36a9fccc8237d79af7987182796b1d9.rbc'
        assert sha(artifact) == artifact.stem
        paths.append(artifact)
        parser_artifact=ROOT/'.work/guarded-local-facts-main-parser-01/artifact.rbc'
        assert sha(parser_artifact)=='a157f60c0356ae2498eaa94a1133e2257c8ee220bcfd3b24ca969525fe5f9a61'
        paths.append(parser_artifact)
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD']).strip()
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        work = ROOT / '.work' / NAME
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen, historical_source_bindings=historical,
            target=str(target.relative_to(ROOT)), same_source_root=True, required_free_bytes=needed,
            allocated_target_bytes=allocated, minimum_child_gib=8, expected_commands=5,
            guest_commands=0, executable_code_publications=0, production_runtime_changes=0, performance_measurement=False))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_', 'CHAIN_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0', CARGO_PROFILE_RELEASE_DEBUG='1', CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0', RUST_TEST_THREADS='2', CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1')
        cargo = ['cargo', '+nightly-2026-09-08', 'test', '--release', '--lib', '-p', 'rust-interp-bytecode',
                 '--locked', '--offline', '--jobs', '2', '--manifest-path', str(ROOT / 'Cargo.toml'), '--target-dir', str(target)]
        commands=[]
        for release in [False,True]:
            command=[x for x in cargo if release or x!='--release']
            commands.append(('controls-'+('release' if release else 'debug'),[*command,'proof::chain_census::controls::'],{},ROOT,4))
        commands.append(('census',[*cargo,'proof::chain_census::observe_saved_scalar_chains','--','--ignored','--exact'],
            dict(CHAIN_ARTIFACT=str(artifact),CHAIN_ARTIFACT_SHA256=artifact.stem,CHAIN_OUTPUT=str(work/'census.json')),ROOT,1))
        commands.append(('python-controls',[sys.executable,'-m','unittest','test_analyze','-v'],{},ROOT/'benchmarks/experiments/native-call-cost-census',2))
        commands.append(('attribute',[sys.executable,str(Path(__file__).with_name('attribute.py')),NAME],{},ROOT,0))
        records = []
        for label, command, extra, cwd, tests in commands:
            require_space(ROOT, 8)
            if command[0] == 'cargo':
                assert shutil.disk_usage(ROOT).free >= needed, 'build admission no longer holds'
            start = time.time()
            child, out, err = capture(command, cwd=cwd, env=env | extra, receipt_path=work / 'active.json', receipt=dict(label=label))
            for stream, payload in [('stdout', out), ('stderr', err)]:
                (work / (label + '.' + stream)).write_text(payload)
            records.append(dict(label=label, command=command, extra_env=extra, pid=child.pid,
                returncode=child.returncode, seconds=time.time() - start,
                stdout_sha256=sha(work / (label + '.stdout')), stderr_sha256=sha(work / (label + '.stderr'))))
            write(work / 'records.json', records)
            assert child.returncode == 0, (out + err)[-6000:]
            if tests:
                if label == 'python-controls':
                    assert 'Ran 2 tests' in err and err.rstrip().endswith('OK')
                else:
                    assert f'test result: ok. {tests} passed; 0 failed; 0 ignored;' in out
            assert all(sha(ROOT / p) == h for p, h in frozen.items())
            print(label, 'passed', flush=True)
        out = ROOT / 'results' / NAME
        out.mkdir(exist_ok=True)
        report=read(out/'attribution.json');assert report['status']=='passed'
        census=read(work/'census.json');assert census['status']=='passed' and census['memory_work_remaining']>0
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        write(out/'summary.json',dict(status='passed',commands=5,controls_per_profile=4,python_controls=2,cases=report['cases'],
            eligible_leaves=report['eligible_leaves'],eligible_chains=report['eligible_chains'],declines=report['declines'],
            setup_seconds=sum(r['seconds'] for r in records),source_revision=revision,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),attribution_sha256=sha(out/'attribution.json'),
            census_sha256={'census':sha(work/'census.json')},
            guest_commands=0,original_project_guest_commands=0,synthetic_reference_evaluations_per_profile=5,
            executable_code_publications=0,production_runtime_changes=0,performance_measurement=False,
            scope='Structural small initialized/confined direct-call DAGs; parent scalar lowering and transaction/resource/profile semantics remain unimplemented.'))
        print(json.dumps(report['cases']),flush=True)



if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build matched main/control and heap-bias VMs with retained strict compiler tools."""
import argparse
import fcntl
import json
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
from interpreter import installed_tools
from workflow_io import capture, require_space, write_json as write

TARGET = ROOT / '.work/fixed-frame-clear-combined-build-01/target'


BASE = 'ab6adbe8'

def admit(rows):
    # Count allocated bytes, conservatively retaining old artifacts while
    # reserving twice the entire populated target for new outputs/linking.
    output=subprocess.check_output(['du','-sk',str(TARGET)],text=True)
    allocated=int(output.split()[0])*1024
    required=max(14*2**30,8*2**30+2*allocated)
    free=shutil.disk_usage(ROOT).free
    rows.append(dict(at=time.time(),target_allocated_bytes=allocated,
        required_free_bytes=required,free_bytes=free))
    assert free>=required, ('setup space admission',rows[-1])


def install_control(work,env,retained,control,admissions):
    source=work/'control-source';source.mkdir()
    revision=subprocess.check_output(['git','rev-parse',BASE],text=True).strip()
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'crates','.cargo',
        'Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()
    files={}
    for name in names:
        body=subprocess.check_output(['git','show',revision+':'+name])
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);files[name]=sha(p)
    write(work/'control-source.json',dict(source_revision=revision,files=files))
    admit(admissions)
    command=['cargo','+nightly-2026-09-08','build','--release','--locked','--offline','--jobs','2',
        '--target-dir',str(TARGET),'-p','rust-interp-bytecode','--bin','rust-interp-vm']
    started=time.time()
    child,out,err=capture(command,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label='matched-control-build'))
    (work/'matched-control.stdout').write_text(out);(work/'matched-control.stderr').write_text(err)
    record=dict(command=command,pid=child.pid,returncode=child.returncode,started_at=started,finished_at=time.time(),
        stdout_sha256=sha(work/'matched-control.stdout'),stderr_sha256=sha(work/'matched-control.stderr'))
    write(work/'matched-control-command.json',record);assert child.returncode==0,err[-4000:]
    assert all(sha(source/p)==h for p,h in files.items())
    binaries=dict(control['binaries']);binaries['rust-interp-vm']=sha(TARGET/'release/rust-interp-vm')
    composition=dict(kind='heap-address-bias-matched-control',schema_version=1,source_commit=revision,
        compiler_source_key=control['tool_key'],binaries=binaries)
    import hashlib
    key=hashlib.sha256(json.dumps(composition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with (ROOT/'.work/interpreter-tools.lock').open('a') as lock:
        acquire_lock(lock,45);installed=ROOT/'.work/interpreter-tools'/key;installed.mkdir(exist_ok=False)
        for name in binaries:
            shutil.copy2(TARGET/'release'/name if name=='rust-interp-vm' else retained/name,installed/name)
        caps=json.loads(subprocess.check_output([str(installed/'rust-interp-mir-export'),'--rust-interp-capabilities'],env=env,text=True))
        caps.update(tool_key=key,exporter_sha256=binaries['rust-interp-mir-export']);write(installed/'capabilities.json',caps)
        write(installed/'source.json',dict(tool_key=key,composition=composition,files=files,source_commit=revision,
            key_algorithm='SHA256 of canonical composition JSON',source=str(source)))
        assert all(sha(installed/n)==h for n,h in binaries.items());write(installed/'ready.json',binaries)
    return dict(tool_key=key,binaries=binaries,composition=composition,
        source_manifest=str((work/'control-source.json').relative_to(ROOT)),source_manifest_sha256=sha(work/'control-source.json'),
        command_record_sha256=sha(work/'matched-control-command.json'),setup_seconds=time.time()-started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--control-build', type=Path, required=True)
    parser.add_argument('--resume-from', choices=['heap-address-build-01'])
    args = parser.parse_args()
    control_path = args.control_build.resolve(strict=True)
    control = json.loads(control_path.read_text())
    assert control['status'] == 'passed'
    CONTROL = control['tool_key']
    assert CONTROL == '35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1'
    run = args.run_id
    assert re.fullmatch(r'heap-address-build-\d{2}', run)
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        from workflow_io import require_space
        admissions=[]
        admit(admissions)
        prior = json.loads((ROOT / '.work/experiments/fixed-frame-clear-combined-build-01/status.json').read_text())
        assert prior['status'] == 'finished' and prior['returncode'] == 0
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).strip()
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        files = [ROOT / name for name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml', 'scripts/compare_saved_runtime.py', 'scripts/workflow_io.py', 'scripts/interpreter.py']]
        files += [Path(__file__).resolve(), Path(__file__).with_name('PLAN.md'), Path(__file__).with_name('QUALIFICATION.md'), control_path]
        files += [p for p in (ROOT / 'crates').rglob('*') if p.is_file() and (p.suffix == '.rs' or p.name == 'Cargo.toml')]
        files += [ROOT / p for p in ['tests/test_isolated_launcher.py','tests/test_interpreter_build_metrics.py']]
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in files}
        retained, _ = installed_tools(CONTROL)
        assert json.loads((retained/'ready.json').read_text()) == control['binaries']
        assert all(sha(retained/name) == digest for name,digest in control['binaries'].items())
        work = ROOT / '.work' / run
        work.mkdir(exist_ok=False)
        write(work / 'plan.json', dict(owner=str(ROOT), source_commit=source, frozen=frozen,
              source=str(ROOT), target=str(TARGET), control=CONTROL, controller_sha256=sha(Path(__file__))))
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
                             'RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never', CARGO_INCREMENTAL='0', CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0', CARGO_PROFILE_RELEASE_DEBUG='1')
        records, counts = [], {}
        setup_started = time.time()
        reused_debug=None
        if args.resume_from:
            previous=ROOT/'.work'/args.resume_from
            final=json.loads((ROOT/'.work/experiments'/args.resume_from/'status.json').read_text())
            assert final['status']=='finished' and final['returncode']==1
            assert sha(ROOT/'.work/experiments'/args.resume_from/'command.log')==final['log_sha256']
            previous_plan=json.loads((previous/'plan.json').read_text())
            for p,h in previous_plan['frozen'].items():
                if p not in ['benchmarks/experiments/heap-address-bias/build.py',
                             'benchmarks/experiments/heap-address-bias/QUALIFICATION.md']:
                    assert sha(ROOT/p)==h,p
            # Only the post-test ignored-count assertion failed. Retain the
            # exact source snapshot and executable already built for control.
            old_record=json.loads((previous/'matched-control-command.json').read_text())
            assert old_record['returncode']==0
            for stream in ['stdout','stderr']:
                assert sha(previous/('matched-control.'+stream))==old_record[stream+'_sha256']
            source_manifest=json.loads((previous/'control-source.json').read_text())
            for p,h in source_manifest['files'].items():
                assert sha(previous/'control-source'/p)==h
            matches=[]
            for p in (ROOT/'.work/interpreter-tools').glob('*/source.json'):
                info=json.loads(p.read_text());composition=info.get('composition',{})
                if composition.get('kind')=='heap-address-bias-matched-control' and info.get('source')==str(previous/'control-source'):
                    matches.append((p,info))
            p,info=matches.pop();assert not matches
            matched=dict(tool_key=info['tool_key'],binaries=info['composition']['binaries'],composition=info['composition'],
                source_manifest=str((previous/'control-source.json').relative_to(ROOT)),source_manifest_sha256=sha(previous/'control-source.json'),
                command_record_sha256=sha(previous/'matched-control-command.json'),
                command_record=str((previous/'matched-control-command.json').relative_to(ROOT)),
                setup_seconds=old_record['finished_at']-old_record['started_at'],reused_from=args.resume_from)
            assert all(sha(p.parent/n)==h for n,h in matched['binaries'].items())
            (reused_debug,)=json.loads((previous/'commands.json').read_text())
            assert reused_debug['label']=='test-debug' and reused_debug['returncode']==0
            for stream in ['stdout','stderr']:
                assert sha(previous/('test-debug.'+stream))==reused_debug[stream+'_sha256']
            write(work/'reuse.json',dict(previous=args.resume_from,terminal=final,
                previous_plan_sha256=sha(previous/'plan.json'),matched_control=matched,debug=reused_debug))
        else:
            matched=install_control(work,env,retained,control,admissions)
        for label, action, profile in [('test-debug', 'test', []), ('test-release', 'test', ['--release']),
                                       ('build-release', 'build', ['--release'])]:
            admit(admissions)
            command = ['cargo', '+nightly-2026-09-08', action, *profile, '--locked', '--offline', '--jobs', '2',
                       '--target-dir', str(TARGET)]
            if action == 'build':
                command += ['-p', 'rust-interp-bytecode', '--bin', 'rust-interp-vm']
            else:
                command += ['--workspace']
            started = time.time()
            if label=='test-debug' and reused_debug:
                assert command==reused_debug['command']
                stdout=(previous/'test-debug.stdout').read_text();stderr=(previous/'test-debug.stderr').read_text()
                from types import SimpleNamespace
                child=SimpleNamespace(pid=reused_debug['pid'],returncode=0)
            else:
                child, stdout, stderr = capture(command, cwd=ROOT, env=env,
                    receipt_path=work / 'active.json', receipt=dict(label=label))
            for suffix, text in [('stdout', stdout), ('stderr', stderr)]:
                (work / f'{label}.{suffix}').write_text(text)
            records.append(dict(label=label, command=command, pid=child.pid, returncode=child.returncode,
                                started_at=started, finished_at=time.time(),
                                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            if label=='test-debug' and reused_debug:
                records[-1].update(reused_from=args.resume_from,original_started_at=reused_debug['started_at'],
                    original_finished_at=reused_debug['finished_at'])
            write(work / 'commands.json', records)
            assert child.returncode == 0, f'{label} failed'
            if action == 'test':
                matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', stdout + stderr)
                assert matches and all(int(failed) == 0 for _, failed in matches)
                counts[label] = sum(int(passed) for passed, _ in matches)
                assert counts[label] >= 504, counts
                for name in ['fixed_checks_match_wide_oracle_and_preserve_cached_values',
                             'dynamic_checks_match_wide_oracle_at_both_tag_bits_and_full_counts',
                             'external_call_guards_preserve_fault_order_partial_copies_and_native_abi',
                             'emitted_preflight_matches_independent_complete_range_oracle']:
                    assert name + ' ... ok' in stdout
                ignored = sum(int(n) for n in re.findall(r'test result: ok\. \d+ passed; \d+ failed; (\d+) ignored;', stdout+stderr))
                assert ignored == 10, ignored
        assert counts['test-debug']==counts['test-release']
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        binaries = json.loads((retained / 'ready.json').read_text())
        for name in ['rust-interp-vm']:
            binaries[name] = sha(TARGET / 'release' / name)
        composition = dict(kind='heap-address-bias-composition', schema_version=1, source_commit=source,
                           compiler_source_key=CONTROL, binaries=binaries)
        import hashlib
        key = hashlib.sha256(json.dumps(composition, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (ROOT / '.work/interpreter-tools.lock').open('a') as publication:
            acquire_lock(publication, 45)
            installed = ROOT / '.work/interpreter-tools' / key
            installed.mkdir(exist_ok=False)
            for name in binaries:
                shutil.copy2(TARGET / 'release' / name if name == 'rust-interp-vm' else retained / name, installed / name)
            caps = json.loads(subprocess.check_output([str(installed / 'rust-interp-mir-export'), '--rust-interp-capabilities'], env=env, text=True))
            caps.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
            write(installed / 'capabilities.json', caps)
            write(installed / 'source.json', dict(tool_key=key, composition=composition, files=frozen,
                  source_commit=source, key_algorithm='SHA256 of canonical composition JSON', source=str(ROOT)))
            write(installed / 'ready.json', binaries)
        out = ROOT / 'results' / run
        out.mkdir(exist_ok=False)
        write(out / 'summary.json', dict(status='passed', source_commit=source, tool_key=key, binaries=binaries,
              composition=composition, matched_control=matched, tests=counts, commands=records, source_manifest=str((work / 'plan.json').relative_to(ROOT)),
              source_manifest_sha256=sha(work / 'plan.json'), raw=str(work.relative_to(ROOT)), performance_measurement=False))
        write(out / 'setup-accounting.json', dict(status='passed', tool_key=key,
            retained_compiler_key=CONTROL, source_commit=source,
            setup_wall_seconds=time.time()-setup_started,
            matched_control=matched, admissions=admissions,
            command_wall_seconds={r['label']:r['finished_at']-r['started_at'] for r in records},
            reused_setup_seconds=sum([matched['setup_seconds'],reused_debug['finished_at']-reused_debug['started_at']]) if reused_debug else 0,
            qualification_summary_sha256=sha(out/'summary.json'),
            definition='Admitted setup through immutable tool installation, including compilation and tests; excludes lock wait. The last VM build alone is not total setup cost.',
            performance_measurement=False))
        print('PASS', counts, key, flush=True)


if __name__ == '__main__':
    main()

"""One frozen current-runtime ES8 edit history, with compiled restoration."""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from common import ROOT, HERE, RUN, SOURCE, CHANGED, inputs, require_protocol, revision, read, sha, write, capture, acquire_lock, require_space
from model import KEY, FLAGS, NAMES, MODES, CUSTOM, states, schedule, command, accounting, native_outcomes, native_executable
from evidence import validate_row, validate_group, expected_status
from workflow_io import SourceEdit
from workflow_measurements import child_usage, child_cpu_since
from workflow_controls import exporter_seconds
from suite_reports import read_report, validate_report

CONTROLS = 'adopted-es8-controller-01'
PROBES = [('type', b'\nfn rust_interp_strict_type_probe() { let _: u32 = "invalid"; }\n', 'E0308'),
          ('borrow', b'\nfn rust_interp_strict_borrow_probe() { let mut x=0; let a=&mut x; let b=&mut x; std::hint::black_box((a,b)); }\n', 'E0499')]


def environment(source):
    env = {k:v for k,v in source.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) and k not in
        ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER',
         'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR', 'RUST_TEST_THREADS', 'PYTHONPATH']}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(CARGO_TERM_COLOR='never', PYTHONDONTWRITEBYTECODE='1', RUST_TEST_THREADS='2',
        CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
    return env, dict(env, RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=' '.join(FLAGS))


def run_history(path, original, variants, probe, run_state):
    """The final build observes SourceEdit's final restored inode and timestamp."""
    assert variants[-1] == ('restored', 'restored-original', original)
    with SourceEdit(path, original) as edit:
        for label, code, diagnostic in PROBES:
            assert b'rust_interp_strict_' not in original
            edit.replace(original+code)
            probe(label, diagnostic)
        for state, label, payload in variants[:-1]:
            edit.replace(payload)
            run_state(state)
    assert path.read_bytes() == original
    run_state('restored')


def require_controller(frozen):
    folder = ROOT/'results'/CONTROLS
    closure = read(folder/'closure.json')
    assert closure['status'] == 'closed' and closure['all_hashes_verified']
    summary = read(folder/'summary.json')
    assert sha(folder/'summary.json') == closure['summary_sha256']
    assert summary['status'] == 'passed' and summary['controls'] == 6 and summary['commands'] == 1
    raw = ROOT/summary['raw']
    assert sha(raw/'plan.json') == summary['plan_sha256']
    for p,h in read(raw/'plan.json')['frozen'].items():
        assert sha(ROOT/p) == h and frozen.setdefault(p,h) == h, p
    for p in [folder/'closure.json', folder/'summary.json', folder/'terminal.json', raw/'plan.json', raw/'records.json']:
        frozen[str(p.relative_to(ROOT))] = sha(p)


def main():
    frozen, original, owner = inputs()
    require_protocol(frozen)
    require_controller(frozen)
    source_revision = revision()
    raw = ROOT/'.work'/RUN
    raw.mkdir(exist_ok=False)
    artifacts = raw/'artifacts'
    artifacts.mkdir()
    (raw/'original.rs').write_bytes(original)
    order = schedule(original)
    env, guest = environment(os.environ)
    write(raw/'plan.json', dict(owner=str(ROOT), source_revision=source_revision, frozen=frozen,
        controller_command=[sys.executable, *sys.orig_argv[1:]], source=str(SOURCE.relative_to(ROOT)),
        revision=owner['revision'], original_source_sha256=sha(CHANGED), schedule=order,
        expected_commands=32, strict_controls=2, names=NAMES, tool_key=KEY,
        cargo_jobs=2, native_threads=2, prepared_workers=2, initial_minimum_gib=16, minimum_child_gib=8,
        guest_rustflags=FLAGS, build_tool_opt_level=0, performance_measurement=True, candidate=False, adoption=False))
    records, strict, space = [], [], []
    previous = dict.fromkeys(MODES)
    for name, value in [('records', records), ('strict', strict), ('space', space)]:
        write(raw/(name+'.json'), value)

    def snapshot(path):
        digest = sha(path)
        target = artifacts/(digest+path.suffix)
        if not target.exists():
            subprocess.run(['cp', '-c', str(path), str(target)], check=True)
        assert sha(target) == digest
        return dict(path=str(target.relative_to(ROOT)), sha256=digest)

    def probe(label, diagnostic):
        require_space(ROOT, 8)
        index = 'strict-'+label
        cmd = command(SOURCE, raw, index, 'custom', raw.name+':strict')
        child, out, err = capture(cmd, cwd=SOURCE, env=guest, receipt_path=raw/(index+'-child.json'), receipt=dict(label=label))
        for stream, value in [('stdout', out), ('stderr', err)]:
            (raw/(index+'.'+stream)).write_text(value)
        strict.append(dict(label=label, command=cmd, pid=child.pid, returncode=child.returncode,
            source_sha256=sha(CHANGED), child_sha256=sha(raw/(index+'-child.json')),
            stdout_sha256=sha(raw/(index+'.stdout')), stderr_sha256=sha(raw/(index+'.stderr'))))
        write(raw/'strict.json', strict)
        assert child.returncode == 101 and diagnostic in err, err[-3000:]
        assert not (raw/(index+'-suite.json')).exists()
        assert 'rust-interp-export: ' not in err and 'rust-interp-launch: ' not in err
        print('strict', label, 'validated', flush=True)

    def run_state(state):
        group = []
        for scheduled in [r for r in order if r['state'] == state]:
            require_space(ROOT, 8)
            index, mode = len(records), scheduled['mode']
            assert previous[mode] != sha(CHANGED) == scheduled['source_sha256']
            cmd = command(SOURCE, raw, index, mode)
            space.append(dict(index=index, phase='before', free_bytes=shutil.disk_usage(ROOT).free))
            write(raw/'space.json', space)
            usage = child_usage()
            start = time.perf_counter()
            child, out, err = capture(cmd, cwd=SOURCE, env=guest if mode in CUSTOM else env,
                receipt_path=raw/(str(index)+'-child.json'), receipt=dict(index=index, **scheduled))
            wall, cpu = time.perf_counter()-start, child_cpu_since(usage)
            for stream, value in [('stdout', out), ('stderr', err)]:
                (raw/(str(index)+'.'+stream)).write_text(value)
            row = dict(scheduled, index=index, command=cmd, pid=child.pid, returncode=child.returncode,
                wall_seconds=wall, cpu_seconds=cpu['total_seconds'], cpu=cpu, previous_source_sha256=previous[mode],
                child_sha256=sha(raw/(str(index)+'-child.json')),
                stdout_sha256=sha(raw/(str(index)+'.stdout')), stderr_sha256=sha(raw/(str(index)+'.stderr')))
            records.append(row)
            write(raw/'records.json', records)
            assert child.returncode == expected_status(state, mode), err[-3000:]
            if mode in CUSTOM:
                launch, = [json.loads(l.split(': ',1)[1]) for l in err.splitlines() if l.startswith('rust-interp-launch: ')]
                report, digest = read_report(raw/(str(index)+'-suite.json'), launch['suite_report_sha256'])
                row.update(launch=launch, suite_sha256=digest, stages=exporter_seconds(err),
                    outcomes=[list(x) for x in validate_report(report, NAMES, 'prepared', state != -1)])
                for field, key in [('artifact', 'artifact_path'), ('catalog', 'entry_catalog_path'),
                                   ('selection', 'test_selection_path'), ('call_report', 'call_report_path')]:
                    row[field] = snapshot(Path(launch[key]))
            elif mode == 'native':
                row['outcomes'] = [list(x) for x in native_outcomes(out, state != -1)]
                row['executable'] = snapshot(native_executable(out, SOURCE, raw/mode))
            write(raw/'records.json', records)
            validate_row(row, raw)
            previous[mode] = sha(CHANGED)
            group.append(row)
            space.append(dict(index=index, phase='after', free_bytes=shutil.disk_usage(ROOT).free))
            write(raw/'space.json', space)
            print(index+1, state, mode, 'validated', flush=True)
        validate_group(group)

    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 16)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        run_history(CHANGED, original, states(original), probe, run_state)
        assert all(h == sha(CHANGED) for h in previous.values())
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=SOURCE).strip()
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN
        result.mkdir(exist_ok=False)
        write(result/'summary.json', dict(status='passed', source_revision=source_revision, commands=32, strict_controls=2,
            original_tests=2, source_restored=True, original_assertions_unchanged=True, exact_native_test_outcomes=True,
            matching_custom_artifacts=True, raw=str(raw.relative_to(ROOT)), tool_key=KEY,
            **{name+'_sha256':sha(raw/(name+'.json')) for name in ['plan', 'records', 'strict', 'space']},
            measurement=accounting(records), performance_measurement=True, candidate=False, adoption=False))
        print('Completed32 commands', flush=True)


if __name__ == '__main__':
    assert len(sys.argv) == 1
    main()

#!/opt/homebrew/bin/python3 -B
"""Small ordinary native Cargo fixture. No timings qualify performance."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
WORK = ROOT / '.work/host-build-opt-fixture-01'
OUT = ROOT / 'results/host-build-opt-fixture-01'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
TOOLCHAIN = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
HOST = 'aarch64-apple-darwin'
BYTE_LIMIT = 256 * 2**20


def require(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def file(path):
    path = Path(path)
    before = stamp(path)
    require(stat.S_ISREG(before[2]), 'ordinary file required: ' + str(path))
    payload = path.read_bytes()
    require(stamp(path) == before, 'file changed during read')
    return dict(path=str(path), sha256=hashlib.sha256(payload).hexdigest(),
                bytes=len(payload), identity=before)


def write(path, value):
    path = Path(path)
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('xb') as stream:
        stream.write(payload)
    os.replace(tmp, path)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def footprint(*, while_running=False):
    logical = allocated = count = 0
    for root in [WORK, OUT]:
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                p = Path(directory) / name
                try:
                    s = p.lstat()
                except FileNotFoundError:
                    if while_running:
                        continue  # Cargo may finish/remove an ordinary temporary.
                    raise
                require(not stat.S_ISLNK(s.st_mode), 'unexpected owned output link')
                count += 1
                require(count <= 8192, 'fixture output entry count')
                if stat.S_ISREG(s.st_mode):
                    logical += s.st_size
                    allocated += s.st_blocks * 512
    return dict(entries=count, logical_bytes=logical, allocated_bytes=allocated)


def invoke(argv, env, label, io):
    directory = OUT / label
    directory.mkdir()
    box = {}
    start = time.monotonic()

    def capture():
        try:
            box['value'] = io.capture(argv, cwd=WORK/'fixture', env=env,
                receipt_path=directory/'record.json', receipt=dict(environment=env,
                    maximum_seconds=30, maximum_output_bytes=BYTE_LIMIT))
        except BaseException as error:
            box['error'] = repr(error)

    thread = threading.Thread(target=capture)
    thread.start()
    breaches = []
    peak = dict(logical_bytes=0, allocated_bytes=0)
    try:
        while thread.is_alive():
            thread.join(.1)
            try:
                current = footprint(while_running=thread.is_alive())
                for key in peak:
                    peak[key] = max(peak[key], current[key])
                if max(current['logical_bytes'], current['allocated_bytes']) > BYTE_LIMIT:
                    breaches.append('output footprint exceeded 256 MiB')
            except BaseException as error:
                breaches.append('output observation failed: ' + repr(error))
            if time.monotonic() - start > 30:
                breaches.append('command exceeded 30 seconds')
            if breaches:
                # No signals, retry, further child, or release of canonical while
                # the owned Cargo child may still run. The threshold is observed,
                # not a kill timer or atomic filesystem reservation.
                thread.join()
    finally:
        thread.join()
    write(directory/'observation.json', dict(violations=sorted(set(breaches)),
        sampled_peak=peak, interval_seconds=.1, hard_wall_limit=False,
        atomic_disk_quota=False, retained_normal_wait=True))
    require('error' not in box, box.get('error', 'capture error'))
    child, stdout, stderr = box['value']
    (directory/'stdout').write_text(stdout)
    (directory/'stderr').write_text(stderr)
    require(len(stdout.encode()) + len(stderr.encode()) <= 8 * 2**20, 'bounded raw output')
    require(not breaches, 'observed command resource threshold failed')
    require(child.returncode == 0, 'native fixture command failed: ' + label)
    require(max(v for k,v in footprint().items() if k != 'entries') <= BYTE_LIMIT,
            'closed output footprint exceeded')
    return stdout, stderr


def option(argv, name):
    found = []
    for i, arg in enumerate(argv):
        if arg == name:
            require(i + 1 < len(argv), 'missing option value')
            found.append(argv[i+1])
        elif arg.startswith(name + '='):
            found.append(arg[len(name)+1:])
    require(len(found) <= 1, 'duplicate option: ' + name)
    return found[0] if found else None


def codegen(argv):
    values = []
    for i, arg in enumerate(argv):
        if arg == '-C':
            values.append(argv[i+1])
        elif arg.startswith('-C'):
            values.append(arg[2:])
    result = {}
    for item in values:
        key, sep, value = item.partition('=')
        require(sep and key not in result, 'duplicate or valueless codegen option')
        result[key.replace('_', '-')] = value
    return result


def validate_calls(directory, level, env):
    rows = []
    for path in sorted(directory.glob('*.json')):
        row = json.loads(path.read_text())
        argv = row['argv'][1:]
        require(row['argv'][0] == str(TOOLCHAIN/'bin/rustc'), 'exact compiler')
        require({k:v for k,v in row['environment'].items() if k.startswith('CARGO_PROFILE_')} ==
            {k:v for k,v in env.items() if k.startswith('CARGO_PROFILE_')}, 'actual profile transport')
        source = [arg for arg in argv if arg.endswith('.rs')]
        if not source:
            require(any(arg in argv for arg in ['-vV', '--print']) or
                    any(arg.startswith('--print=') for arg in argv), 'unknown compiler query')
            continue
        require(len(source) == 1, 'ordinary fixture compiler input')
        name = option(argv, '--crate-name')
        target = option(argv, '--target')
        require(target in [None, HOST], 'exact host/target route')
        host = target is None
        cg = codegen(argv)
        actual_opt = cg.get('opt-level', '0')
        require(actual_opt == str(level if host else 1), 'host/target opt level differs')
        debug = cg.get('debug-assertions', 'yes' if actual_opt == '0' else 'no')
        require(debug in ['true', 'yes', 'on', '1'], 'debug assertions disabled')
        require(cg.get('overflow-checks', debug) in ['true', 'yes', 'on', '1'], 'overflow checks disabled')
        out = Path(option(argv, '--out-dir'))
        require(out.is_relative_to(WORK/('target-' + str(level))), 'fresh selected target directory')
        package = Path(row['environment']['CARGO_MANIFEST_DIR']).name
        require(package in ['host','shared','target'], 'local fixture package')
        rows.append(dict(source=file(path), crate=name, package=package, host=host,
            crate_type=option(argv, '--crate-type'), test='--test' in argv, codegen=cg,
            unstable_options=[argv[i+1] if arg == '-Z' else arg[2:]
                for i,arg in enumerate(argv) if arg == '-Z' or arg.startswith('-Z')],
            build_profile={k:row['environment'].get(k) for k in ['OPT_LEVEL', 'DEBUG']}))
    libraries = [r for r in rows if r['crate'] != 'build_script_build']
    roles = [(r['crate'], r['host'], r['test']) for r in libraries]
    expected = {('profile_shared_fixture', True, False),
        ('profile_shared_fixture', False, False), ('profile_host_fixture', True, False),
        ('profile_target_fixture', False, True)}
    require(len(roles) == len(expected) and set(roles) == expected,
            'missing/duplicated host/shared/target fixture compile')
    scripts = [r for r in rows if r['crate'] == 'build_script_build']
    require({r['package'] for r in scripts} == {'host','shared','target'} and
            all(r['host'] and not r['test'] for r in scripts) and
            sum(r['package'] == 'host' for r in scripts) == 1 and
            sum(r['package'] == 'target' for r in scripts) == 1 and
            sum(r['package'] == 'shared' for r in scripts) in [1,2],
            'exact three local build-script source roles')
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources-sha256', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == R, 'exact -B / unoptimized / R cwd')
    manifest_path = HERE/'qualification-sources.json'
    require(file(manifest_path)['sha256'] == args.sources_sha256, 'source manifest digest')
    sources = json.loads(manifest_path.read_text())
    before = {p: file(p) for p in sources['files']}
    require(all(before[p]['sha256'] == digest for p,digest in sources['files'].items()), 'source mismatch')
    io = load(R/'scripts/workflow_io.py', 'hostqual_workflow_io')
    native = load(R/'scripts/workflow_controls.py', 'hostqual_workflow_controls')
    profiles = load(HERE/'host_build_profiles.py', 'hostqual_profiles')
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh fixture output namespaces')
    with LOCK.open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(shutil.disk_usage(ROOT).free >= 2**30, 'fixture requires 1 GiB free entry space')
        WORK.mkdir(); OUT.mkdir()
        record = dict(status='running', pid=os.getpid(), parent_pid=os.getppid(),
            started_at=time.time(), argv=sys.argv, cwd=os.getcwd(), source_manifest=file(manifest_path),
            compiler_calls_completed=False, benchmark=False, command_limit_seconds=30,
            output_limit_bytes=BYTE_LIMIT, no_signals=True)
        write(OUT/'record.json', record); write(OUT/'source-before.json', before)
        try:
            shutil.copytree(HERE/'qualification-fixture', WORK/'fixture')
            (WORK/'cargo-home').mkdir(); (WORK/'tmp').mkdir()
            for directory in [WORK/'fixture', *(WORK/'fixture').parents]:
                for name in ['config', 'config.toml']:
                    require(not os.path.lexists(directory/'.cargo'/name), 'ambient Cargo configuration')
            base = {k:os.environ[k] for k in ['HOME', 'PATH', 'USER', 'LOGNAME'] if k in os.environ}
            base.update(CARGO_HOME=str(WORK/'cargo-home'), TMPDIR=str(WORK/'tmp'),
                CARGO_INCREMENTAL='0', CARGO_TERM_COLOR='never', CARGO_NET_OFFLINE='true',
                RUSTC=str(TOOLCHAIN/'bin/rustc'), RUSTC_WORKSPACE_WRAPPER='',
                RUSTFLAGS='', CARGO_ENCODED_RUSTFLAGS='', LC_ALL='C', LANG='C',
                PYTHONDONTWRITEBYTECODE='1', RUST_BACKTRACE='0')
            tools_before = {name:native.file_identity(TOOLCHAIN/'bin'/name) for name in ['cargo','rustc']}
            write(OUT/'tools-before.json', tools_before)
            for name in ['cargo','rustc']:
                stdout, _ = invoke([str(TOOLCHAIN/'bin'/name), '-vV'], base, name+'-version', io)
                require(stdout.startswith(name+' '), 'native version')
                if name == 'rustc': require('\nhost: '+HOST+'\n' in stdout, 'native host')
            reports = []
            for level in [0,3]:
                trace = WORK/('trace-' + str(level)); trace.mkdir()
                selected = dict(policy=profiles.POLICY, modes=dict(native=level,baseline=level,candidate=level))
                env = native.native_environment(profiles.environment(base, selected, 'native'), 'repository', [])
                env.update(RUSTC_WRAPPER=str(HERE/'qualification-capture.py'), HOSTQUAL_TRACE=str(trace),
                           HOSTQUAL_EXPECTED_LEVEL=str(level))
                argv = native.native_command('nightly-2026-09-08', WORK/'fixture/Cargo.toml',
                    'profile-target-fixture', WORK/('target-'+str(level)), 2, '1', ['profile_contract'],
                    cargo=TOOLCHAIN/'bin/cargo')
                separator = argv.index('--')
                argv[separator:separator] = ['--target', HOST, '--message-format=json-render-diagnostics']
                stdout, _ = invoke(argv, env, 'host-'+str(level), io)
                require('test result: ok. 1 passed; 0 failed;' in stdout, 'exact actual native test success')
                calls = validate_calls(trace, level, env)
                events = [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
                script_profiles = []
                for event in events:
                    if event.get('reason') == 'build-script-executed':
                        path = Path(event['out_dir'])/'profile.json'
                        require(path.is_relative_to(WORK/('target-'+str(level))), 'owned build-script record')
                        value = json.loads(path.read_text())
                        require(set(value) == {'package','opt_level','debug'}, 'build-script record schema')
                        is_target = HOST in path.relative_to(WORK/('target-'+str(level))).parts
                        require(value['debug'] in ['true','false'] and
                                (not is_target or value['debug'] == 'true') and
                                value['opt_level'] == str(1 if is_target else level),
                                'actual host/target build-script profile')
                        script_profiles.append(dict(source=file(path), value=value,
                            target=is_target, cargo_event=event))
                require(len(script_profiles) == 4, 'host/shared/target build-script observations')
                require(sorted((r['value']['package'], r['value']['opt_level']) for r in script_profiles) ==
                    sorted([('profile-host-fixture',str(level)), ('profile-shared-fixture',str(level)),
                        ('profile-shared-fixture','1'), ('profile-target-fixture','1')]),
                    'complete actual build-script profile roles')
                reports.append(dict(level=level, calls=calls, build_scripts=script_profiles,
                    target=str(WORK/('target-'+str(level))), test='profile_contract'))
            def comparable(report):
                return sorted((r['crate'],r['package'],r['host'],r['test'],tuple(r['unstable_options']),
                    json.dumps({k:v for k,v in r['codegen'].items()
                        if k not in ['opt-level','metadata','extra-filename',
                                     'debug-assertions','overflow-checks']},sort_keys=True))
                    for r in report['calls'])
            require(comparable(reports[0]) == comparable(reports[1]),
                    'non-optimization compiler codegen policy changed across profiles')
            require(sorted((r['value']['package'],r['target'],r['value']['debug'])
                        for r in reports[0]['build_scripts']) ==
                    sorted((r['value']['package'],r['target'],r['value']['debug'])
                        for r in reports[1]['build_scripts']), 'build-script DEBUG changed')
            fixture_rows = {}
            for p in sorted((HERE/'qualification-fixture').rglob('*')):
                if p.is_file():
                    copied = WORK/'fixture'/p.relative_to(HERE/'qualification-fixture')
                    require(file(p)['sha256'] == file(copied)['sha256'], 'fixture source or lockfile changed')
                    fixture_rows[str(copied)] = file(copied)
            write(OUT/'fixture-after.json', fixture_rows)
            after = {p:file(p) for p in sources['files']}
            require(after == before, 'source changed')
            tools_after = {name:native.file_identity(TOOLCHAIN/'bin'/name) for name in ['cargo','rustc']}
            require(tools_after == tools_before, 'native tool changed')
            write(OUT/'source-after.json', after); write(OUT/'tools-after.json', tools_after)
            result = dict(status='passed', arms=reports, footprint=footprint(),
                source_manifest=file(manifest_path), benchmark=False, performance_qualified=False,
                scope='local host/target Cargo profile transport, build-script inputs, cfg and overflow checks')
            write(OUT/'result.json', result)
            record.update(status='passed', compiler_calls_completed=True, result=file(OUT/'result.json'))
        except BaseException as error:
            record.update(status='failed', error=repr(error))
            raise
        finally:
            record.update(finished_at=time.time())
            write(OUT/'record.json', record)


if __name__ == '__main__':
    main()

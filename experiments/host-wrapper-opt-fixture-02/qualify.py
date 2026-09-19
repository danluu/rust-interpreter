#!/opt/homebrew/bin/python3 -B
"""Real Cargo host-wrapper qualification; no performance result or exporter claim."""
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
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
WORK = ROOT / '.work/host-wrapper-opt-fixture-02'
OUT = ROOT / 'results/host-wrapper-opt-fixture-02'
HOST = 'aarch64-apple-darwin'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(value, message):
    if not value:
        raise RuntimeError(message)


def authenticate_source(path):
    path = Path(path)
    def stamp():
        s = path.lstat()
        return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns]
    before = stamp()
    require(path.is_absolute() and stat.S_ISREG(before[2]), 'ordinary absolute source required')
    digest = hashlib.sha256()
    length = 0
    with path.open('rb') as stream:
        while block := stream.read(2**20):
            length += len(block)
            digest.update(block)
    require(length == before[4] and stamp() == before, 'source changed while authenticating')
    return dict(path=str(path),sha256=digest.hexdigest(),bytes=length,identity=before)


def check_calls(utils, original_dir, final_dir, mode, runtime):
    """Check exact suffixes at the actual compiler boundary, matched by exec PID."""
    rows = []
    final_paths = set(final_dir.glob('*.argv'))
    originals = sorted(original_dir.glob('*.json'))
    require(0 < len(originals) <= 64, 'bounded actual compiler calls')
    for path in originals:
        row = json.loads(path.read_text())
        original = row['argv']
        require(original[0] == runtime['executable']['path'], 'actual bound runtime compiler')
        require(not any(k.startswith('CARGO_PROFILE_') for k in row['environment']),
                'Cargo profile environment was changed')
        require(row['environment']['RUST_INTERP_HOST_CODEGEN_OPT'] == mode, 'mode transport')
        final_path = final_dir / ('native-' + str(row['pid']) + '.argv')
        require(final_path in final_paths, 'missing same-PID final compiler boundary')
        final_paths.remove(final_path)
        fields = final_path.read_bytes().decode().split('\0')
        require(fields[:4] == ['rust-interp-compiler-argv-v1', 'native',
            runtime['default_sysroot'], row['cwd']] and fields[-1] == '', 'compiler boundary header')
        argv = original[1:]
        target = utils.option(argv, '--target')
        require(target in [None, HOST], 'host or explicit native target only')
        sources = [x for x in argv if x.endswith('.rs')]
        query = not sources
        if query:
            require(any(x in argv for x in ['-vV', '--print']) or
                any(x.startswith('--print=') for x in argv), 'known Cargo query')
        else:
            require(len(sources) == 1, 'one actual Rust source')
        # Cargo's filename query legitimately repeats --crate-type. The existing
        # router adds its MIR suffix if any separated type includes lib/rlib.
        kinds = [argv[i+1] if arg == '--crate-type' else arg.partition('=')[2]
            for i,arg in enumerate(argv) if arg == '--crate-type' or arg.startswith('--crate-type=')]
        kind = None if query else utils.option(argv, '--crate-type')
        emits = utils.option(argv, '--emit')
        linked = emits is not None and any(x.partition('=')[0] == 'link' for x in emits.split(','))
        library = any(t in ['lib','rlib'] for types in kinds for t in types.split(','))
        eligible = not query and target is None and '--test' not in argv and linked and (
            library or kind == 'proc-macro')
        expected = original + ['-Zstable-cgu-partitioning=no']
        if target is not None:
            require(utils.option(argv, '--sysroot') is None, 'no original explicit guest sysroot')
            expected += ['--sysroot', runtime['default_sysroot']]
        if library:
            expected += ['-Zalways-encode-mir=yes']
        cg = utils.codegen(argv)
        if mode == 'on' and eligible:
            require('opt-level' not in cg and 'lto' not in cg, 'ordinary unoptimized host input')
            expected += ['-Copt-level=3', '-Zmir-opt-level=1', '-Clto=off']
            if 'debug-assertions' not in cg:
                expected += ['-Cdebug-assertions=yes']
            if 'overflow-checks' not in cg:
                debug = cg.get('debug-assertions', 'yes')
                require(debug in ['yes','no','true','false','on','off','y','n'], 'known debug setting')
                expected += ['-Coverflow-checks=' + ('no' if debug in ['no','false','off','n'] else 'yes')]
        require(fields[4:-1] == expected, 'unexpected actual compiler argv: ' + str(path))
        final_cg = utils.codegen(fields[5:-1])
        if not query:
            opt = final_cg.get('opt-level', '0')
            require(opt == ('1' if target else '3' if mode == 'on' and eligible else '0'),
                    'actual host/target optimization level')
            debug = final_cg.get('debug-assertions', 'yes' if opt == '0' else 'no')
            require(debug in ['yes','true','on','y'] and
                final_cg.get('overflow-checks', debug) in ['yes','true','on','y'], 'checks disabled')
        externs = []
        for i, arg in enumerate(argv):
            if arg == '--extern':
                name, separator, value = argv[i+1].partition('=')
                if not separator:
                    require(name == 'proc_macro' and kind == 'proc-macro' and target is None,
                            'unknown pathless extern in native fixture')
                    externs.append(dict(name=name, artifact=None, source='bound-runtime-sysroot'))
                else:
                    require(Path(value).is_relative_to(WORK/('target-'+mode)), 'owned actual extern')
                    externs.append(dict(name=name, artifact=utils.file(value)))
        rows.append(dict(original=utils.file(path), final=utils.file(final_path),
            argv=original, crate=utils.option(argv, '--crate-name'),
            package=row['environment'].get('CARGO_PKG_NAME'), host=target is None,
            test='--test' in argv, query=query, eligible=eligible, original_codegen=cg,
            final_codegen=final_cg, externs=externs))
    require(not final_paths, 'unmatched final compiler calls')
    compiles = [r for r in rows if not r['query']]
    ordinary = [r for r in compiles if r['crate'] != 'build_script_build']
    require({(r['crate'],r['host'],r['test']) for r in ordinary} == {
        ('profile_shared_fixture',True,False), ('profile_shared_fixture',False,False),
        ('profile_host_fixture',True,False), ('profile_target_fixture',False,True)}
        and len(ordinary) == 4, 'complete distinct host/shared/target roles')
    require(sum(r['eligible'] for r in rows) == 2, 'exactly host shared library and macro eligible')
    scripts = [r for r in compiles if r['crate'] == 'build_script_build']
    require({r['package'] for r in scripts} == {
        'profile-host-fixture','profile-shared-fixture','profile-target-fixture'} and
        all(r['host'] and not r['test'] and not r['eligible'] for r in scripts) and
        sum(r['package'] == 'profile-host-fixture' for r in scripts) == 1 and
        sum(r['package'] == 'profile-target-fixture' for r in scripts) == 1 and
        sum(r['package'] == 'profile-shared-fixture' for r in scripts) in [1,2],
        'exact excluded build-script role multiplicities')
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--binding-sha256', required=True)
    args = parser.parse_args()
    require(sys.dont_write_bytecode and not sys.flags.optimize and Path.cwd() == R,
            'exact -B / unoptimized Python / R cwd')
    payload = args.binding.read_bytes()
    require(hashlib.sha256(payload).hexdigest() == args.binding_sha256, 'fixture binding hash')
    binding = json.loads(payload)
    require(binding['schema_version'] == 1 and binding['policy'] == 'host-codegen-opt-v1', 'binding schema')
    utility = ROOT/'experiments/host-build-opt-01/qualify-fixture-02.py'
    required = {HERE/'qualify.py',HERE/'capture.py',utility,
        R/'scripts/workflow_controls.py',R/'scripts/workflow_io.py',Path(binding['generated_roles'])}
    required.update(Path(binding['wrapper_main']).parent/name for name in [
        'wrapper_main.rs','wrapper_route.rs','host_proc_macro.rs','compiler_roles.rs',
        'compiler_file_identity.rs','compiler_argv.rs','main.rs'])
    required.update(p for p in (ROOT/'experiments/host-build-opt-01/qualification-fixture').rglob('*') if p.is_file())
    require(all(str(p) in binding['sources'] for p in required), 'incomplete executable/fixture source closure')
    before = {p:authenticate_source(p) for p in binding['sources']}
    require(all(before[p]['sha256'] == sha for p,sha in binding['sources'].items()), 'source binding changed')
    # Reuse the closed native fixture's process capture/resource observer, not its profile policy.
    utils = load(utility, 'wrapper_fixture_utilities')
    utils.WORK = WORK
    utils.OUT = OUT
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh fixture namespace')
    native = load(R/'scripts/workflow_controls.py', 'wrapper_fixture_native')
    io = load(R/'scripts/workflow_io.py', 'wrapper_fixture_io')
    roles = binding['compiler_roles']
    runtime = roles['runtime']
    with LOCK.open('r') as lock:
        deadline = time.monotonic() + 600
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'canonical lock wait exceeded 600 seconds')
                time.sleep(.1)
        require(shutil.disk_usage(ROOT).free >= 2**30, 'fixture entry requires 1 GiB free')
        WORK.mkdir(); OUT.mkdir()
        record = dict(status='running', pid=os.getpid(), parent_pid=os.getppid(),
            started_at=time.time(), argv=sys.argv, cwd=str(Path.cwd()), binding=utils.file(args.binding),
            benchmark=False, performance_qualified=False, bytecode_qualified=False, no_signals=True)
        utils.write(OUT/'record.json', record)
        utils.write(OUT/'source-before.json', before)
        try:
            shutil.copytree(ROOT/'experiments/host-build-opt-01/qualification-fixture', WORK/'fixture')
            for name in ['cargo-home','tmp','generated','tools']:
                (WORK/name).mkdir()
            for directory in [WORK/'fixture', *(WORK/'fixture').parents]:
                for name in ['config','config.toml']:
                    require(not os.path.lexists(directory/'.cargo'/name), 'ambient Cargo configuration')
            base = {k:os.environ[k] for k in ['HOME','PATH','USER','LOGNAME'] if k in os.environ}
            base.update(CARGO_HOME=str(WORK/'cargo-home'), TMPDIR=str(WORK/'tmp'), CARGO_INCREMENTAL='0',
                CARGO_TERM_COLOR='never', CARGO_NET_OFFLINE='true', RUSTC_WORKSPACE_WRAPPER='',
                RUSTC_WRAPPER='', RUSTFLAGS='', CARGO_ENCODED_RUSTFLAGS='', LANG='C', LC_ALL='C',
                PYTHONDONTWRITEBYTECODE='1', RUST_BACKTRACE='0')
            tools_before = {p:native.file_identity(p) for p in binding['tools']}
            require(all(tools_before[p]['sha256'] == sha for p,sha in binding['tools'].items()), 'physical tool binding')
            utils.write(OUT/'tools-before.json', tools_before)
            shutil.copyfile(binding['generated_roles'], WORK/'generated/compiler_roles.rs')
            wrapper = WORK/'tools/rust-interp-rustc-wrapper'
            build_env = dict(base, OUT_DIR=str(WORK/'generated'),
                RUST_INTERP_SYSROOT=runtime['default_sysroot'],
                RUST_INTERP_RUNTIME_COMPILER=runtime['executable']['path'],
                RUST_INTERP_RUSTC_COMMIT=roles['runtime_source_commit'])
            require('--sysroot='+binding['build_sysroot'] in roles['build_rustflags'],
                    'bound build sysroot flags')
            build = [roles['build']['executable']['path'], '--edition=2024',
                *roles['build_rustflags'], '-Copt-level=1', '-Cdebuginfo=0',
                binding['wrapper_main'], '-o', str(wrapper)]
            utils.invoke(build, build_env, 'build-wrapper', io)
            built = native.file_identity(wrapper)
            stdout, _ = utils.invoke([str(wrapper), '--rust-interp-compiler-roles'], base, 'wrapper-roles', io)
            require(json.loads(stdout) == roles, 'actual wrapper compiler association')
            stdout, _ = utils.invoke([str(wrapper), '--rust-interp-host-codegen-capability'], base, 'wrapper-policy', io)
            lines = stdout.splitlines()
            require(len(lines) == 3 and json.loads(lines[0]) == binding['capability'] and
                lines[1] == runtime['default_sysroot'] and json.loads(lines[2]) == roles,
                'actual wrapper capability/sysroot/compiler-role binding')
            for label, executable, expected in [
                ('cargo', binding['cargo'], binding['cargo_version']),
                ('runtime', runtime['executable']['path'], runtime['verbose_version']),
                ('build', roles['build']['executable']['path'], roles['build']['verbose_version'])]:
                stdout, _ = utils.invoke([executable, '-vV'], base, label+'-version', io)
                require(stdout == expected, 'exact '+label+' version')
            reports = []
            for mode in ['off','on']:
                trace = WORK/('trace-'+mode); trace.mkdir()
                final = WORK/('final-'+mode); final.mkdir()
                target = WORK/('target-'+mode)
                env = dict(base, RUSTC=runtime['executable']['path'], RUSTC_WRAPPER=str(HERE/'capture.py'),
                    HOSTQUAL_TRACE=str(trace), HOSTQUAL_WRAPPER=str(wrapper), HOSTQUAL_EXPECTED_LEVEL='0',
                    RUST_INTERP_COMPILER_RUSTC=runtime['executable']['path'],
                    RUST_INTERP_STABLE_CGU_PARTITIONING='off', RUST_INTERP_HOST_CODEGEN_OPT=mode,
                    RUST_INTERP_STD_SYSROOT=runtime['default_sysroot'], RUST_INTERP_STD_TARGET=HOST,
                    RUST_INTERP_EXPORT_PACKAGE='unselected-fixture-package',
                    RUST_INTERP_COMPILER_ARGV_RECORD_DIR=str(final))
                argv = native.native_command('nightly-2026-09-08', WORK/'fixture/Cargo.toml',
                    'profile-target-fixture', target, 2, '1', ['profile_contract'], cargo=Path(binding['cargo']))
                index = argv.index('--')
                argv[index:index] = ['--target', HOST, '--message-format=json-render-diagnostics']
                stdout, _ = utils.invoke(argv, env, 'cargo-'+mode, io)
                require('test result: ok. 1 passed; 0 failed;' in stdout, 'actual native fixture test')
                calls = check_calls(utils, trace, final, mode, runtime)
                profiles = []
                for line in stdout.splitlines():
                    if not line.startswith('{'):
                        continue
                    event = json.loads(line)
                    if event.get('reason') != 'build-script-executed':
                        continue
                    path = Path(event['out_dir'])/'profile.json'
                    require(path.is_relative_to(target), 'owned build-script observation')
                    value = json.loads(path.read_text())
                    is_target = HOST in path.relative_to(target).parts
                    require(set(value) == {'package','opt_level','debug'} and
                        value['opt_level'] == ('1' if is_target else '0'), 'Cargo-visible optimization changed')
                    profiles.append(dict(source=utils.file(path), value=value, target=is_target))
                require(len(profiles) == 4 and sorted((p['value']['package'],p['target']) for p in profiles) ==
                    sorted([('profile-host-fixture',False),('profile-shared-fixture',False),
                        ('profile-shared-fixture',True),('profile-target-fixture',True)]), 'four build profile roles')
                reports.append(dict(mode=mode, calls=calls, build_scripts=profiles))
            def original_calls(report):
                prefix = str(WORK/('target-'+report['mode']))
                return sorted(json.dumps([arg.replace(prefix, '<target>') for arg in row['argv']])
                    for row in report['calls'])
            require(original_calls(reports[0]) == original_calls(reports[1]),
                'Cargo argv changed beyond the explicit target directory; includes crate metadata/extern names')
            def profile_values(report):
                return sorted(json.dumps([p['target'],p['value']],sort_keys=True) for p in report['build_scripts'])
            require(profile_values(reports[0]) == profile_values(reports[1]), 'build-script OPT_LEVEL/DEBUG changed')
            after = {p:utils.file(p) for p in binding['sources']}
            require(after == before, 'source changed during qualification')
            tools_after = {p:native.file_identity(p) for p in binding['tools']}
            require(tools_after == tools_before and native.file_identity(wrapper) == built, 'tool changed')
            fixture_after = {}
            for source in sorted((ROOT/'experiments/host-build-opt-01/qualification-fixture').rglob('*')):
                if source.is_file():
                    copied = WORK/'fixture'/source.relative_to(ROOT/'experiments/host-build-opt-01/qualification-fixture')
                    require(utils.file(source)['sha256'] == utils.file(copied)['sha256'], 'fixture or lockfile changed')
                    fixture_after[str(copied)] = utils.file(copied)
            utils.write(OUT/'fixture-after.json', fixture_after)
            utils.write(OUT/'source-after.json', after)
            utils.write(OUT/'tools-after.json', tools_after)
            result = dict(status='passed', arms=reports, wrapper=built, footprint=utils.footprint(),
                benchmark=False, performance_qualified=False, bytecode_qualified=False,
                scope='combined native host wrapper, original/final argv, Cargo inputs, checks and target identities')
            utils.write(OUT/'result.json', result)
            record.update(status='passed', result=utils.file(OUT/'result.json'))
        except BaseException as error:
            record.update(status='failed', error=repr(error))
            raise
        finally:
            record.update(finished_at=time.time())
            utils.write(OUT/'record.json', record)


if __name__ == '__main__':
    main()

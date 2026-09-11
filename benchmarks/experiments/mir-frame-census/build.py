"""Build an isolated exporter observer; retain the exact production VM."""
import fcntl, hashlib, json, os, re, shutil, subprocess, time
from pathlib import Path
root = Path(__file__).resolve().parents[3]
experiment = Path(__file__).resolve().parent
lock = (root / '.work/benchmark.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((root / p).read_text())
def write(p, value): p.write_text(json.dumps(value, indent=2) + '\n')
parent = read('.work/local-memory-forwarding-experimental-57a5/manifest.json')
frozen = parent['files'] | {str(p.relative_to(root)): sha(p) for p in experiment.iterdir() if p.is_file()}
def verify(): assert all(sha(root / p) == h for p, h in frozen.items())
verify(); assert shutil.disk_usage(root).free > 3 * 1024**3
work = root / '.work/mir-frame-census-build-01'; work.mkdir()
source = work / 'tool-source'; source.mkdir(); (source / 'scripts').mkdir()
for name in ['Cargo.toml', 'Cargo.lock']: shutil.copy2(root / name, source / name)
shutil.copytree(root / 'crates', source / 'crates')
shutil.copy2(root / 'scripts/interpreter.py', source / 'scripts/interpreter.py')
p = source / 'crates/mir-export/src/lower.rs'; text = p.read_text()
assert text.count('mod scalar_promote;') == 1 and text.count('        scalar_promote::apply(&mut self)?;') == 1
text = text.replace('mod scalar_promote;', 'mod scalar_promote;\nmod frame_census;')
text = text.replace('        scalar_promote::apply(&mut self)?;', '        scalar_promote::apply(&mut self)?;\n        frame_census::observe(&self);')
p.write_text(text)
shutil.copy2(experiment / 'observe.rs', source / 'crates/mir-export/src/lower/frame_census.rs')
inputs = [source / 'Cargo.toml', source / 'Cargo.lock']
for crate in ['bytecode', 'mir-export']:
    inputs += sorted((source / 'crates' / crate).rglob('*.rs'))
    inputs.append(source / 'crates' / crate / 'Cargo.toml')
fingerprint = hashlib.sha256()
for p in inputs: fingerprint.update(str(p.relative_to(source)).encode() + b'\0' + p.read_bytes())
key = fingerprint.hexdigest()
copied = {str(p.relative_to(source)): sha(p) for p in inputs + [source / 'scripts/interpreter.py']}
write(work / 'provenance.json', dict(parent_tool_key=parent['tool_key'], source_key=key,
    source=str(source.relative_to(root)), root_frozen=frozen, copied_inputs=copied, diagnostic_only=True))
env = os.environ.copy()
for n in list(env):
    if n.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or n in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']: env.pop(n)
env['CARGO_TERM_COLOR'] = 'never'
target = root / '.work/diagnostic-builds/mir-frame-census-01'; assert not target.exists()
records = []
try:
    for label, action, packages in [('build', 'build', ['rust-interp-bytecode','rust-interp-mir-export']), ('exporter-tests', 'test', ['rust-interp-mir-export'])]:
        verify(); assert all(sha(source / p) == h for p, h in copied.items())
        command = ['cargo', '+nightly-2026-09-08', action, '--release', '--locked', '--offline', '--jobs', '2',
            '--manifest-path', str(source / 'Cargo.toml'), '--target-dir', str(target)]
        for package in packages: command += ['-p', package]
        with (work / (label + '.log')).open('x') as log:
            child = subprocess.Popen(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
            record = dict(pid=child.pid, parent_pid=os.getpid(), cwd=str(source), command=command,
                label=label, status='running', started_at=time.time())
            write(work / 'active-command.json', record); print('START', label, child.pid, flush=True)
            code = child.wait()
        record.update(status='finished', returncode=code, finished_at=time.time())
        records.append(record); write(work / 'records.json', records); write(work / 'active-command.json', record)
        assert code == 0, (label, code)
    tests = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed;', (work / 'exporter-tests.log').read_text())
    assert sum(int(n) for n,_ in tests) == 11 and all(failed == '0' for _,failed in tests)
    binaries = {name: sha(target / 'release' / name) for name in parent['binaries']}
    assert binaries['rust-interp-vm'] == parent['binaries']['rust-interp-vm']
    tool = root / '.work/interpreter-tools' / key
    with (root / '.work/interpreter-tools.lock').open('a') as tool_lock:
        fcntl.flock(tool_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not tool.exists(); tool.mkdir()
        for name in binaries: shutil.copy2(target / 'release' / name, tool / name)
        probe = subprocess.run([str(tool / 'rust-interp-mir-export'), '--rust-interp-capabilities'], capture_output=True, text=True, check=True)
        capabilities = json.loads(probe.stdout); assert capabilities['schema_version'] == 1
        capabilities.update(tool_key=key, exporter_sha256=binaries['rust-interp-mir-export'])
        write(tool / 'capabilities.json', capabilities); write(tool / 'ready.json', binaries)
    verify(); assert all(sha(source / p) == h for p,h in copied.items())
    write(work / 'summary.json', dict(status='Isolated MIR frame observer built; exact retained VM; 11 exporter tests pass',
        tool_key=key, parent_tool_key=parent['tool_key'], binaries=binaries, exporter_tests=11,
        source=str(source.relative_to(root)), target=str(target.relative_to(root)), root_unchanged=True,
        performance_measurement=False, artifact_qualification_pending=True))
    print(json.dumps(dict(tool_key=key, binaries=binaries, exporter_tests=11)), flush=True)
except BaseException as error:
    write(work / 'failure.json', dict(error=repr(error), root_unchanged=all(sha(root / p) == h for p,h in frozen.items())))
    raise

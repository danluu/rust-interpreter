"""Fresh diagnostic exports must preserve the exact original tested bytecode."""
import fcntl, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
root = Path(__file__).resolve().parents[3]
lock = (root / '.work/benchmark.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((root / p).read_text())
def write(p, value): p.write_text(json.dumps(value, indent=2) + '\n')
build = read('.work/mir-frame-census-build-01/summary.json')
proof = read('.work/mir-frame-census-build-01/provenance.json')
assert build['exporter_tests'] == 11
frozen = proof['root_frozen'] | {str(Path(__file__).relative_to(root)): sha(Path(__file__))}
source = root / '.work/sources/fre'
owner = read(source / '.rust-interp-owned.json')
def verify():
    assert owner['owner'] == str(root)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == owner['revision']
    assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip()
    assert all(sha(root / p) == h for p,h in frozen.items())
    assert all(sha(root / proof['source'] / p) == h for p,h in proof['copied_inputs'].items())
    assert all(sha(root / '.work/interpreter-tools' / build['tool_key'] / n) == h for n,h in build['binaries'].items())
verify()
work = root / '.work/mir-frame-census-collection-01'; work.mkdir()
results = []
for label in ['folded-literal-trie', 'token-phrase']:
    old = next(r for r in read(f'.work/runs/paired-local-memory-forwarding-{label}-01/records.json') if r['state'] == 0 and r['mode'] == 'candidate')
    assert len(old['calls']) == 1 and len(old['artifacts']) == 1
    call = old['calls'][0]; command = call['command'].copy(); command[0] = sys.executable
    frozen[str(Path(command[1]).relative_to(root))] = sha(Path(command[1]))
    command[command.index('--tool-key') + 1] = build['tool_key']
    command[command.index('--cache-namespace') + 1] = 'mir-frame-census-' + label + '-01'
    env = os.environ.copy()
    for n in list(env):
        if n.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or n in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']: env.pop(n)
    env.update(CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1', RUSTFLAGS=call['rustflags'])
    if label == 'token-phrase':
        env.update(CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL='0', CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL='0')
    verify()
    with (work / (label + '.stdout')).open('x') as output, (work / (label + '.stderr')).open('x') as errors:
        child = subprocess.Popen(command, cwd=root, env=env, stdout=output, stderr=errors)
        record = dict(pid=child.pid, parent_pid=os.getpid(), command=command, cwd=str(root), label=label,
                      status='running', started_at=time.time(), rustflags=call['rustflags'])
        write(work / 'active-command.json', record); print('START', label, child.pid, flush=True)
        code = child.wait()
    record.update(status='finished', returncode=code, finished_at=time.time()); write(work / 'active-command.json', record)
    assert code == 0 and (work / (label + '.stdout')).read_text().strip() == '0'
    errors = (work / (label + '.stderr')).read_text()
    inventories = [json.loads(line.removeprefix('rust-interp-frame-census: ')) for line in errors.splitlines() if line.startswith('rust-interp-frame-census: ')]
    launches = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in errors.splitlines() if line.startswith('rust-interp-launch: ')]
    assert len(launches) == 1 and inventories
    launch = launches[0]; assert launch['tool_key'] == build['tool_key']
    artifact = Path(launch['artifact_path'])
    assert launch['artifact_sha256'] == sha(artifact) == old['artifacts'][0]['sha256']
    assert re.search(r'jit_declined_functions=0\b', errors)
    verify()
    row = dict(label=label, command=record, artifact=str(artifact.relative_to(root)), artifact_sha256=sha(artifact),
        artifact_bytes=artifact.stat().st_size, identical_to_retained=True, original_tests_pass=True,
        inventories=inventories, performance_measurement=False,
        files={str(p.relative_to(root)): sha(p) for p in [work / (label + '.stdout'),work / (label + '.stderr')]})
    write(work / (label + '.json'), row); results.append(row)
    print(json.dumps(dict(label=label, functions=len(inventories), artifact_identical=True,
        unreferenced_bytes=sum(r['semantically_unreferenced_mir_bytes'] for r in inventories),
        unnamed_bytes=sum(r['non_abi_mir_bytes_without_named_local_address'] for r in inventories))), flush=True)
verify()
write(work / 'summary.json', dict(status='Fresh MIR inventories preserve both original bytecode artifacts and assertions',
    tool_key=build['tool_key'], retained_tool_key=build['parent_tool_key'], binaries=build['binaries'],
    source_unchanged=True, cases=results, frozen=frozen, performance_measurement=False))

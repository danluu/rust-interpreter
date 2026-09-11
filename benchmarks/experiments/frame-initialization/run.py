"""Build a typed census and inspect the two saved original execution profiles."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[3]
source = Path(__file__).resolve().parent
lock = (root / '.work/benchmark.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((root / p).read_text())
def write(p, d): p.write_text(json.dumps(d, indent=2) + '\n')
parent = read('.work/local-memory-forwarding-experimental-57a5/manifest.json')
work = root / '.work/frame-initialization-census-01'; work.mkdir()
target = root / '.work/diagnostic-builds/frame-initialization-census-01'
assert not target.exists()
frozen = parent['files'] | {str(p.relative_to(root)): sha(p) for p in source.iterdir() if p.is_file()}
cases = [dict(label=label,
    artifact=f'.work/runs/paired-scalar-packed-cache-{name}-01/artifacts/candidate/0-0.rbc',
    profile=f'.work/local-memory-forwarding-screen-01/{label}-profile-candidate.json')
    for label, name in [('folded', 'folded-literal-trie'), ('token-phrase', 'token-phrase')]]
for case in cases:
    for field in ['artifact', 'profile']:
        case[field + '_sha256'] = sha(root / case[field])
        frozen[case[field]] = case[field + '_sha256']
write(work / 'plan.json', dict(parent_tool_key=parent['tool_key'], cases=cases, frozen=frozen,
    target=str(target.relative_to(root)), performance_measurement=False))
def verify(): assert all(sha(root / p) == h for p, h in frozen.items())
verify()
env = os.environ.copy()
for n in list(env):
    if n.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or n in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
        env.pop(n)
env['CARGO_TERM_COLOR'] = 'never'
commands = []
def invoke(label, command):
    verify()
    with (work / (label + '.stdout')).open('x') as output, (work / (label + '.stderr')).open('x') as errors:
        child = subprocess.Popen(command, cwd=root, env=env, stdout=output, stderr=errors)
        record = dict(label=label, pid=child.pid, parent_pid=os.getpid(), command=command,
                      cwd=str(root), started_at=time.time(), status='running')
        write(work / 'active-command.json', record)
        print('START', label, child.pid, flush=True)
        code = child.wait()
    record.update(status='finished', returncode=code, finished_at=time.time())
    write(work / 'active-command.json', record); commands.append(record); write(work / 'commands.json', commands)
    assert code == 0, (label, code)
    verify()
manifest = source / 'Cargo.toml'
if not (source / 'Cargo.lock').exists():
    invoke('lockfile', ['cargo', '+nightly-2026-09-08', 'generate-lockfile', '--offline', '--manifest-path', str(manifest)])
frozen[str((source / 'Cargo.lock').relative_to(root))] = sha(source / 'Cargo.lock')
invoke('build', ['cargo', '+nightly-2026-09-08', 'build', '--release', '--locked', '--offline', '--jobs', '2',
    '--manifest-path', str(manifest), '--target-dir', str(target)])
binary = target / 'release/frame-initialization-census'
results = []
for case in cases:
    invoke(case['label'], [str(binary), str(root / case['artifact']), str(root / case['profile'])])
    result = read(work / (case['label'] + '.stdout'))
    assert result['performance_measurement'] is False
    results.append(case | dict(census=result))
    print(json.dumps(dict(label=case['label'], local=result['proven_local'], unknown=result['unknown_sources'],
        indirect=result['indirect_calls_without_target_attribution'], instructions=result['instructions'])), flush=True)
verify()
summary = dict(status='Completed typed census on original folded and token profiles',
    parent_tool_key=parent['tool_key'], binary_sha256=sha(binary), cases=results,
    source_unchanged=True, performance_measurement=False, frozen=frozen)
write(work / 'summary.json', summary)

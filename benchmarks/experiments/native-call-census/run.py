"""Inspect saved profiles under the benchmark lock; never re-run guest tests."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def fragment(text):
    start = 'fn branch(op: &Op) -> bool {'
    end = '// Generated regions return small continuation indices on success.'
    assert text.count(start) == text.count(end) == 1
    return text[text.index(start):text.index(end)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--wait-for-lock', type=int, default=0)
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError('Python -O disables diagnostic verification')
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('run-id must be a directory name')
    if not 0 <= args.wait_for_lock <= 600:
        parser.error('wait-for-lock must be 0..600 seconds')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    deadline = time.monotonic() + args.wait_for_lock
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    work = ROOT / '.work' / args.run_id
    work.mkdir(exist_ok=False)
    archived = work / 'source'
    archived.mkdir()
    for path in SOURCE.iterdir():
        if path.is_file():
            (archived / path.name).write_bytes(path.read_bytes())
    target = ROOT / '.work/diagnostic-builds' / args.run_id
    assert not target.exists()
    prior_path = ROOT / 'results/frame-initialization-census-01/summary.json'
    prior = json.loads(prior_path.read_text())
    cases = []
    for label, name in [('folded', 'folded-literal-trie'), ('token-phrase', 'token-phrase')]:
        reference = next(c for c in prior['cases'] if c['label'] == label)
        case = dict(label=label,
            artifact=f'.work/runs/paired-scalar-packed-cache-{name}-01/artifacts/candidate/0-0.rbc',
            profile=f'.work/local-memory-forwarding-screen-01/{label}-profile-candidate.json')
        for field in ['artifact', 'profile']:
            case[field + '_sha256'] = sha(ROOT / case[field])
            assert case[field + '_sha256'] == reference[field + '_sha256']
        cases.append(case)
    current_support = fragment((ROOT / 'crates/bytecode/src/jit.rs').read_text())
    old_support = fragment(subprocess.check_output(
        ['git', 'show', '6b2c61f:crates/bytecode/src/jit.rs'], cwd=ROOT, text=True))
    assert current_support == old_support, 'profile-era emitter eligibility changed'
    paths = [prior_path, ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'rust-toolchain.toml']
    paths += [p for p in (ROOT / 'crates/bytecode').rglob('*') if p.is_file() and
              (p.suffix == '.rs' or p.name == 'Cargo.toml')]
    paths += [p for p in SOURCE.iterdir() if p.is_file()]
    paths += [ROOT / c[k] for c in cases for k in ['artifact', 'profile']]
    frozen = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    plan = dict(owner=str(ROOT), performance_measurement=False, cases=cases,
        profile_tool_key=prior['tool_key'], support_source_commit='6b2c61f',
        support_fragment_sha256=hashlib.sha256(current_support.encode()).hexdigest(),
        current_support_identical_to_profile_era=True, frozen=frozen,
        target=str(target.relative_to(ROOT)))
    write(work / 'plan.json', plan)

    def verify():
        assert all(sha(ROOT / p) == h for p, h in frozen.items()), 'diagnostic inputs changed'

    env = os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
            'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
            'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET']:
            env.pop(name)
    env['CARGO_TERM_COLOR'] = 'never'
    commands = []

    def invoke(label, command):
        verify()
        with (work / (label + '.stdout')).open('x') as output, (work / (label + '.stderr')).open('x') as errors:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=errors)
            record = dict(status='running', label=label, pid=child.pid, parent_pid=os.getpid(),
                          cwd=str(ROOT), command=command, started_at=time.time())
            write(work / 'active-command.json', record)
            print('START', label, child.pid, flush=True)
            code = child.wait()
        record.update(status='finished', returncode=code, finished_at=time.time())
        write(work / 'active-command.json', record)
        commands.append(record)
        write(work / 'commands.json', commands)
        assert code == 0, (label, code)
        verify()

    manifest = SOURCE / 'Cargo.toml'
    cargo = ['cargo', '+nightly-2026-09-08']
    if not (SOURCE / 'Cargo.lock').exists():
        invoke('lockfile', cargo + ['generate-lockfile', '--offline', '--manifest-path', str(manifest)])
        frozen[str((SOURCE / 'Cargo.lock').relative_to(ROOT))] = sha(SOURCE / 'Cargo.lock')
        (archived / 'Cargo.lock').write_bytes((SOURCE / 'Cargo.lock').read_bytes())
        write(work / 'plan.json', plan)
    options = ['--release', '--locked', '--offline', '--jobs', '2', '--manifest-path', str(manifest),
               '--target-dir', str(target)]
    invoke('tests', cargo + ['test'] + options)
    invoke('build', cargo + ['build'] + options)
    binary = target / 'release/native-call-census'
    summaries = []
    for case in cases:
        invoke(case['label'], [str(binary), str(ROOT / case['artifact']), str(ROOT / case['profile'])])
        result_path = work / (case['label'] + '.stdout')
        result = json.loads(result_path.read_text())
        reference = next(c for c in prior['cases'] if c['label'] == case['label'])
        assert result['instructions'] == reference['instructions']
        all_calls = result['groups']['all_direct']
        assert all_calls['calls'] == reference['proven_local']['calls'] + reference['unknown_sources']['calls']
        assert all_calls['proven_local_argument_calls'] == reference['proven_local']['calls']
        assert result['indirect_calls_without_target_attribution'] == reference['indirect_calls']
        summary = {k: v for k, v in result.items() if k != 'callees'}
        summary.update(case, raw_census=str(result_path.relative_to(ROOT)), raw_census_sha256=sha(result_path),
            top_leaf_callees=[r for r in result['callees'] if r['strict_leaf']][:20],
            top_excluded_callees=[r for r in result['callees'] if not r['strict_leaf']][:20],
            matched_independent_frame_census=True)
        summaries.append(summary)
        print(json.dumps(dict(label=case['label'], groups=result['groups'])), flush=True)
    verify()
    report = dict(status='Completed typed native-call eligibility census', performance_measurement=False,
                  plan=plan, binary_sha256=sha(binary), cases=summaries)
    write(work / 'summary.json', report)
    public = ROOT / 'results' / args.run_id
    public.mkdir(exist_ok=False)
    write(public / 'summary.json', report)


if __name__ == '__main__':
    main()

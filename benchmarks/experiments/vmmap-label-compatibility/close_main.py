"""Close merged-main diagnostic contracts and verify later integration inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write


def read(path):
    return json.loads(path.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        name = 'vmmap-main-contracts-01'
        raw, out = ROOT / '.work' / name, ROOT / 'results' / name
        plan, record, summary = [read(p) for p in [raw / 'plan.json', raw / 'record.json', out / 'summary.json']]
        pub = Path(plan['worktree'])
        git = lambda *args: subprocess.check_output(['git', *args], cwd=pub, text=True).strip()
        assert git('status', '--porcelain') == ''
        assert summary['status'] == 'passed' and summary['python'] == dict(discovered=478, passed=456, skipped=22)
        assert sha(raw / 'plan.json') == summary['plan_sha256']
        assert sha(raw / 'record.json') == summary['record_sha256'] and record['returncode'] == 0
        assert plan['source_revision'] == summary['source_revision']
        # Remote changes may be merged after testing only if every tested input
        # and the complete tracked input inventory remain identical.
        inventory = git('ls-files', 'scripts', 'tests', 'crates', 'Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml').splitlines()
        assert set(inventory) == set(plan['frozen'])
        bindings = {}
        for path, digest in plan['frozen'].items():
            assert sha(pub / path) == digest
            blob = subprocess.check_output(['git', 'show', plan['source_revision'] + ':' + path], cwd=pub)
            assert hashlib.sha256(blob).hexdigest() == digest
            bindings[path] = dict(revision=plan['source_revision'], sha256=digest)
        outer = ROOT / '.work/experiments' / name
        terminal = read(outer / 'status.json')
        assert terminal['status'] == 'finished' and terminal['returncode'] == 0
        assert terminal['plan_sha256'] == sha(outer / 'plan.json')
        assert terminal['log_sha256'] == sha(outer / 'command.log')
        evidence = {str(p.relative_to(ROOT)): sha(p) for p in [
            raw / 'plan.json', raw / 'record.json', outer / 'status.json', outer / 'plan.json', outer / 'command.log']}
        for stream in ['stdout', 'stderr']:
            p = raw / stream
            assert sha(p) == record[stream + '_sha256']
            evidence[str(p.relative_to(ROOT))] = sha(p)
        qualified = ROOT / 'results/vmmap-label-compatibility-01'
        receipt = read(qualified / 'closure.json')
        assert receipt['status'] == 'closed' and receipt['all_hashes_verified']
        assert sha(qualified / 'summary.json') == receipt['summary_sha256'] == plan['qualified_replay_summary_sha256']
        for name in ['summary.json', 'closure.json']:
            p = qualified / name
            evidence[str(p.relative_to(ROOT))] = sha(p)
        assert not (out / 'closure.json').exists()
        write(raw / 'source-bindings.json', bindings)
        write(raw / 'closed-evidence.json', evidence)
        (out / 'terminal.json').write_bytes((outer / 'status.json').read_bytes())
        write(out / 'closure.json', dict(status='closed', all_hashes_verified=True,
            source_revision=plan['source_revision'], integration_revision=git('rev-parse', 'HEAD'),
            integration_source_inventory_unchanged=True, source_files=len(bindings),
            source_bindings=str((raw / 'source-bindings.json').relative_to(ROOT)),
            source_bindings_sha256=sha(raw / 'source-bindings.json'),
            evidence=str((raw / 'closed-evidence.json').relative_to(ROOT)),
            evidence_sha256=sha(raw / 'closed-evidence.json'),
            summary_sha256=sha(out / 'summary.json'), terminal_sha256=sha(out / 'terminal.json'),
            new_guest_commands=0, performance_measurement=False))
        print('Closed merged diagnostic fix:', len(bindings), 'unchanged tested inputs', flush=True)


if __name__ == '__main__':
    main()

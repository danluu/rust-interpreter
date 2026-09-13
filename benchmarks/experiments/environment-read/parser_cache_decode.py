"""Refresh the diagnostic lockfile offline, then decode the preserved mismatch."""
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 8)
        failed = ROOT / '.work/parser-cache-difference-01'
        outer = ROOT / '.work/experiments/parser-cache-difference-01'
        terminal = json.loads((outer / 'status.json').read_text())
        assert terminal['status'] == 'finished' and terminal['returncode'] == 1
        rows = json.loads((failed / 'records.json').read_text())
        assert len(rows) == 1 and rows[0]['returncode'] == 101
        assert 'cannot update the lock file' in (failed / '0.stderr').read_text()
        for stream in ['stdout', 'stderr']:
            assert sha(failed / ('0.' + stream)) == rows[0][stream + '_sha256']
        report = ROOT / 'results/parser-cache-difference-01-failure'; report.mkdir(exist_ok=False)
        write(report / 'summary.json', dict(status='diagnostic lockfile outdated', commands=1,
            compiler_commands_executed=0, decoder_commands=0, guest_commands=0,
            raw=str(failed.relative_to(ROOT)), records_sha256=sha(failed / 'records.json'), terminal=terminal))
        proof_path = ROOT / 'results/pgrust-parser-edits-incremental-01-failure/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['commands'] == 22 and proof['source_restored']
        paths = [ROOT / a['path'] for a in proof['artifacts']]
        assert [sha(p) for p in paths] == [a['sha256'] for a in proof['artifacts']]
        work = ROOT / '.work/parser-cache-difference-02'; work.mkdir(exist_ok=False)
        manifest = ROOT / 'benchmarks/experiments/artifact-diff/Cargo.toml'
        lockfile = manifest.with_name('Cargo.lock')
        shutil.copy2(lockfile, work / 'Cargo.lock.before')
        source_paths = [Path(__file__), manifest, manifest.with_name('main.rs'), ROOT / 'crates/bytecode/Cargo.toml', proof_path, *paths]
        source_paths += list((ROOT / 'crates/bytecode/src').rglob('*.rs'))
        frozen = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
        write(work / 'plan.json', dict(owner=str(ROOT), frozen=frozen,
            lockfile_before_sha256=sha(lockfile), allowed_mutation=str(lockfile.relative_to(ROOT)),
            commands=3, guest_commands=0, performance_measurement=False))
        target = ROOT / '.work/fixed-frame-clear-combined-build-01/target'
        commands = [
            ['cargo', '+nightly-2026-09-08', 'update', '--workspace', '--offline', '--manifest-path', str(manifest)],
            rows[0]['command'], [str(target / 'release/artifact-diff'), *map(str, paths)],
        ]
        env = {k: v for k, v in os.environ.items() if not k.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_'))
               and k not in ['RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC', 'RUSTC_WRAPPER',
                             'RUSTC_WORKSPACE_WRAPPER', 'CARGO_INCREMENTAL', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET', 'CARGO_BUILD_BUILD_DIR']}
        env['CARGO_TERM_COLOR'] = 'never'; records = []
        for index, command in enumerate(commands):
            require_space(ROOT, 8)
            child, out, err = capture(command, cwd=ROOT, env=env, receipt_path=work / 'active.json', receipt=dict(index=index))
            (work / f'{index}.stdout').write_text(out); (work / f'{index}.stderr').write_text(err)
            records.append(dict(command=command, pid=child.pid, returncode=child.returncode,
                stdout_sha256=sha(work / f'{index}.stdout'), stderr_sha256=sha(work / f'{index}.stderr')))
            write(work / 'records.json', records); assert child.returncode == 0
            if index == 0: shutil.copy2(lockfile, work / 'Cargo.lock.after')
        assert all(sha(ROOT / p) == h for p, h in frozen.items())
        result = ROOT / 'results/parser-cache-difference-02'; result.mkdir(exist_ok=False)
        write(result / 'difference.json', json.loads((work / '2.stdout').read_text()))
        write(result / 'summary.json', dict(status='passed', commands=3, guest_commands=0,
            decoder_sha256=sha(target / 'release/artifact-diff'), raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work / 'plan.json'), records_sha256=sha(work / 'records.json'),
            lockfile_before_sha256=sha(work / 'Cargo.lock.before'), lockfile_after_sha256=sha(lockfile),
            difference_sha256=sha(result / 'difference.json'), equivalence_proof=False))
        print('PASS: saved parser artifacts structurally compared; no guest executed', flush=True)


if __name__ == '__main__':
    main()

"""Retire only receipt-derived compiler intermediates from the closed bounded-scalar ES8 screen."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import require_space, write_json as write

RUN = 'closed-bounded-scalar-es8-cache-retirement-01'
HISTORIES = [('bounded-scalar-padding-screen-es8-02', 40)]


def identity(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and path.resolve(strict=True) == path, path
    return dict(device=info.st_dev, inode=info.st_ino, size=info.st_size, blocks=info.st_blocks,
                links=info.st_nlink, mtime_ns=info.st_mtime_ns, mode=info.st_mode)


def check_open(root):
    check = subprocess.run(['lsof', '-Fpn', '+D', str(root)], text=True, capture_output=True)
    assert not check.stderr and check.returncode in [0, 1], (root, check.stderr)
    fields = check.stdout.splitlines()
    if root.parent.parent == ROOT / '.work/interpreter-workspaces':
        assert len(fields) == 3 and fields[0] == 'p' + str(os.getpid())
        assert fields[1].startswith('f') and fields[1][1:].isdigit()
        assert fields[2] == 'n' + str(root / 'invocation.lock'), (root, fields)
    else:
        assert not fields and check.returncode == 1, (root, fields)
    return dict(root=str(root.relative_to(ROOT)), returncode=check.returncode, stdout=check.stdout)


def main():
    with ExitStack() as stack:
        lock = stack.enter_context((ROOT / '.work/benchmark.lock').open('a'))
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        raw = ROOT / '.work' / RUN
        raw.mkdir(exist_ok=False)
        roots, proofs, historical, pids = set(), {}, [], set()

        def bind(path, expected=None):
            assert path.resolve(strict=True) == path and path.is_file(), path
            digest = sha(path)
            assert expected is None or digest == expected, path
            key = str(path.relative_to(ROOT))
            assert key not in proofs or proofs[key] == digest
            proofs[key] = digest
            return json.loads(path.read_text()) if path.suffix == '.json' else digest

        for name, count in HISTORIES:
            base, out, outer = ROOT / '.work' / name, ROOT / 'results' / name, ROOT / '.work/experiments' / name
            closed = bind(out / 'closure.json')
            assert closed['status'] == 'closed' and closed['all_hashes_verified'] and closed['complete']
            summary = bind(out / 'summary.json', closed['summary_sha256'])
            terminal = bind(out / 'terminal.json', closed['terminal_sha256'])
            assert terminal['owner'] == terminal['cwd'] == str(ROOT)
            assert terminal['status'] == 'finished' and terminal['returncode'] == 0
            bind(outer / 'status.json', sha(out / 'terminal.json'))
            bind(outer / 'plan.json', terminal['plan_sha256'])
            bind(outer / 'command.log', terminal['log_sha256'])
            pids.update([terminal['child_pid'], terminal['supervisor_pid']])
            bindings = bind(ROOT / closed['bindings'], closed['bindings_sha256'])
            evidence = bind(ROOT / closed['evidence'], closed['evidence_sha256'])
            assert len(bindings) == closed['frozen_inputs'] and len(evidence) == closed['evidence_files']
            for path, item in bindings.items():
                if item['kind'] == 'retained':
                    bind(ROOT / path, item['sha256'])
                else:
                    assert item['kind'] == 'git'
                    source = item['revision'] + ':' + path
                    data = subprocess.check_output(['git', 'show', source], cwd=ROOT)
                    assert hashlib.sha256(data).hexdigest() == item['sha256'], source
                    historical.append(dict(run=name, path=path, git_source=source, sha256=item['sha256']))
            for path, digest in evidence.items():
                bind(ROOT / path, digest)
            assert summary['status'] == 'passed' and summary['commands'] == count and summary['strict_controls'] == 2
            assert all(summary[k] for k in ['source_restored', 'original_assertions_unchanged',
                                           'exact_native_test_outcomes', 'matching_custom_artifacts'])
            assert not summary['adoption']
            plan = bind(base / 'plan.json', summary['plan_sha256'])
            rows = bind(base / 'records.json', summary['records_sha256'])
            strict = bind(base / 'strict.json', summary['strict_sha256'])
            assert plan['owner'] == str(ROOT) and len(rows) == count and len(strict) == 2
            source = ROOT / plan['source']
            assert source == ROOT / '.work/sources/fre'
            owner = bind(source / '.rust-interp-owned.json')
            assert owner['owner'] == str(ROOT) and owner['revision'] == plan['revision']
            assert plan['revision'] == 'e0df0b010b156b030a02f073588d28703f4267f3'
            assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == plan['revision']
            assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source).strip()
            bind(source / 'crates/fre-kernels/src/forward_anchored.rs', plan['original_source_sha256'])
            previous = {}
            for row in rows:
                pids.add(row['pid'])
                mode, command = row['mode'], row['command']
                assert row['previous_source_sha256'] == previous.get(mode) != row['source_sha256']
                previous[mode] = row['source_sha256']
                assert command[command.index('--manifest-path') + 1] == str(source / 'Cargo.toml')
                child = bind(base / (str(row['index']) + '-child.json'), row['child_sha256'])
                assert child['status'] == 'finished' and child['pid'] == row['pid']
                assert child['parent_pid'] == terminal['child_pid'] and child['command'] == command
                assert child['returncode'] == row['returncode']
                for stream in ['stdout', 'stderr']:
                    bind(base / (str(row['index']) + '.' + stream), row[stream + '_sha256'])
                if mode in ['native', 'check']:
                    target = Path(command[command.index('--target-dir') + 1])
                    assert target == base / mode
                else:
                    assert mode in ['custom', 'duplicate', 'candidate']
                    launch = row['launch']
                    key = plan['candidate_tool_key'] if mode == 'candidate' else plan['tool_key']
                    assert launch['tool_key'] == key == command[command.index('--tool-key') + 1]
                    assert command[command.index('--cache-namespace') + 1] == name + ':' + mode
                    target = Path(launch['workspace_path'])
                    assert target.parent == ROOT / '.work/interpreter-workspaces' / key
                roots.add(target)
            assert all(value == plan['original_source_sha256'] for value in previous.values())
            for row in strict:
                assert row['returncode'] == 101
                pids.add(row['pid'])
                err = (base / ('strict-' + row['label'] + '.stderr')).read_text()
                assert 'rust-interp-launch: ' not in err and 'rust-interp-export: ' not in err
        assert len(roots) == 5
        roots = sorted(roots)
        assert all(p.resolve(strict=True) == p for p in roots)
        check = subprocess.run(['ps', '-p', ','.join(map(str, sorted(pids))), '-o', 'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
        assert check.returncode in [0, 1] and not check.stderr
        assert not any(name in line for name, _ in HISTORIES for line in check.stdout.splitlines()[1:])
        for root in roots:
            if root.parent.parent == ROOT / '.work/interpreter-workspaces':
                invocation = stack.enter_context((root / 'invocation.lock').open('r+'))
                acquire_lock(invocation, 45)
        write(raw / 'historical-sources.json', historical)
        protected = dict(proofs)
        protected[str((raw / 'historical-sources.json').relative_to(ROOT))] = sha(raw / 'historical-sources.json')
        rows, sizes, open_checks = [], [], []
        for root in roots:
            open_checks.append(check_open(root))
            begin = len(rows)
            for path in root.rglob('*'):
                assert not path.is_symlink(), path
                if not path.is_file():
                    continue
                info = identity(path)
                parts = path.relative_to(root).parts
                compiler = incremental = False
                for prefix in [('debug',), ('target', 'debug'), ('target', 'aarch64-apple-darwin', 'debug')]:
                    if parts[:len(prefix)] == prefix and len(parts) > len(prefix):
                        section = parts[len(prefix)]
                        compiler = section in ['incremental', 'build', 'deps']
                        incremental = section == 'incremental'
                remove = compiler and (incremental or path.suffix in ['.o', '.rlib', '.rmeta'])
                remove = remove and not info['mode'] & 0o111
                remove = remove and path.suffix not in ['.rbc', '.dylib', '.a', '.rs', '.toml', '.lock'] and '.rbc.' not in path.name
                key = str(path.relative_to(ROOT))
                if remove and key not in protected:
                    rows.append(dict(path=key, **info))
                else:
                    protected[key] = sha(path)
            sizes.append(dict(path=str(root.relative_to(ROOT)), files=len(rows) - begin,
                              logical_bytes=sum(r['size'] for r in rows[begin:])))
            print(sizes[-1], flush=True)
        for name, _ in HISTORIES:
            base = ROOT / '.work' / name
            for path in base.rglob('*'):
                if not path.is_file() or path.relative_to(base).parts[0] in ['native', 'check']:
                    continue
                assert not path.is_symlink()
                protected[str(path.relative_to(ROOT))] = sha(path)
        write(raw / 'inventory.json', rows)
        write(raw / 'protected.json', protected)
        assert rows
        before, started = shutil.disk_usage(ROOT).free, time.time()
        write(raw / 'plan.json', dict(owner=str(ROOT), script_sha256=sha(Path(__file__)), roots=sizes,
              process_check=dict(returncode=check.returncode, stdout=check.stdout), open_checks=open_checks,
              files=len(rows), logical_bytes=sum(r['size'] for r in rows), free_before=before,
              completed_histories=[name for name, _ in HISTORIES], started_at=started))
        assert all(sha(ROOT / p) == h for p, h in protected.items())
        for root in roots:
            check_open(root)
        for row in rows:
            path = ROOT / row['path']
            current = identity(path)
            assert all(current[k] == row[k] for k in ['device', 'inode', 'size', 'mtime_ns', 'mode']), path
            path.unlink()
        assert all(sha(ROOT / p) == h for p, h in protected.items())
        assert all(not (ROOT / row['path']).exists() for row in rows)
        write(raw / 'summary.json', dict(status='passed', files_removed=len(rows),
              logical_bytes_removed=sum(r['size'] for r in rows), free_before=before,
              free_after=shutil.disk_usage(ROOT).free, started_at=started, finished_at=time.time(),
              protected_files=len(protected), all_protected_hashes_unchanged=True,
              inventory_sha256=sha(raw / 'inventory.json'), protected_manifest_sha256=sha(raw / 'protected.json'),
              plan_sha256=sha(raw / 'plan.json'), raw=str(raw.relative_to(ROOT)), performance_measurement=False,
              completed_histories=1, completed_commands=40, strict_controls=2))


if __name__ == '__main__':
    assert len(sys.argv) == 1
    main()

#!/usr/bin/env python3
"""Archive saved task-owned retirement evidence; never inspect or delete live caches.

This one-use evidence packager deliberately excludes complete host ps/lsof output.
It replays the saved inspector's candidate filter before publishing its excerpts.
"""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
OUT = Path(__file__).resolve().parent
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def replay_filter(directory, inspection):
    roots = [row['path'] for row in inspection['candidates']]
    inodes = set()
    with gzip.open(directory / 'inventory.jsonl.gz', 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if stat.S_ISREG(row['mode']):
                inodes.add((row['device'], row['inode']))
    result = dict(scope='saved current-user visibility; candidate paths or regular-file device/inode',
                  full_host_tables_published=False, saved_raw_tables_retained_locally=True)
    for label in ['processes', 'handles']:
        payload = (directory / (label + '.stdout')).read_bytes()
        lines = payload.decode().splitlines()
        error = (directory / (label + '.stderr')).read_bytes()
        if label == 'processes':
            found = [line for line in lines if any(root in line for root in roots)]
            assert found == inspection['matching_process_lines'] == []
        else:
            found, process, entry = [], {}, {}
            def finish():
                name = entry.get('n', '')
                exact = any(name == p or name.startswith(p + '/') for p in roots)
                try:
                    inode = (int(entry.get('D', ''), 16), int(entry.get('i', '')))
                except ValueError:
                    inode = None
                if exact or inode in inodes:
                    found.append(dict(process=process.copy(), file=entry.copy(),
                                      path_match=exact, inode_match=inode in inodes))
            for line in lines:
                if not line:
                    continue
                field, value = line[0], line[1:]
                if field == 'p':
                    finish(); entry = {}; process = {'pid': value}
                elif field == 'c':
                    process['command'] = value
                elif field == 'f':
                    finish(); entry = {'fd': value}
                else:
                    entry[field] = value
            finish()
            assert found == inspection['matching_open_handles'] == []
        assert inspection[label + '_returncode'] == 0 and not error
        result[label] = dict(raw_path=str(directory / (label + '.stdout')),
            raw_sha256=sha(payload), raw_bytes=len(payload), raw_lines=len(lines),
            matching=found, returncode=inspection[label + '_returncode'],
            stderr_sha256=sha(error), stderr_bytes=len(error),
            process_receipt=label + '-process.json')
    return result


def main():
    work = ROOT / '.work/compiler-cache-retirement-evidence-01'
    work.mkdir(exist_ok=False)
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(),
        argv=sys.argv, cwd=os.getcwd(), started_at=time.time(), lock=str(LOCK),
        workload='saved evidence packaging only', children_started=0,
        candidate_reinspections=0, deletions=0)
    def save():
        (work / 'receipt.json').write_bytes(encoded(receipt))
    save()
    try:
        with LOCK.open('r+') as lock:
            acquire_lock(lock, 600)
            receipt['lock_acquired_at'] = time.time()
            save()
            members, manifest = {}, {}
            def add(name, path=None, payload=None, derived=False):
                assert name not in members and not name.startswith('/') and '..' not in Path(name).parts
                assert (path is None) != (payload is None)
                if path is not None:
                    assert path.is_file() and not path.is_symlink()
                    payload = path.read_bytes()
                assert isinstance(payload, bytes)
                members[name] = payload
                manifest[name] = dict(sha256=sha(payload), bytes=len(payload),
                    source=str(path) if path is not None else None, derived=derived)
            attempts = {}
            for number in ['01', '02', '03', '04']:
                directory = ROOT / ('.work/cache-retirement-admission-' + number)
                names = ['plan.json']
                names += ['inspect.py'] if number in ['01', '02'] else ['retirement_candidate_inspector.py']
                if number != '03':
                    names += ['inspection.json']
                    attempts[number] = json.loads((directory / 'inspection.json').read_bytes())
                if number in ['01', '04']:
                    names += ['inventory.jsonl.gz', 'processes-process.json', 'handles-process.json']
                    filtered = replay_filter(directory, attempts[number])
                    add('inspection-' + number + '/quiescence-filtered.json',
                        payload=encoded(filtered), derived=True)
                if number == '02':
                    names += ['self-import-diagnosis.json', 'signal-revalidation.json', 'nested-wait-receipt.json']
                if number == '04':
                    names += ['recommendations.json']
                for name in names:
                    add('inspection-' + number + '/' + name, directory / name)
            add('inspection-03/unrun.json', payload=encoded(dict(status='never executed; superseded by 04',
                source='inspection-04/plan.json superseded_unrun_attempt')), derived=True)
            plan = json.loads((ROOT / '.work/cache-retirement-admission-04/plan.json').read_bytes())
            for path, expected in plan['ownership_receipts'].items():
                path = Path(path)
                payload = path.read_bytes()
                assert sha(payload) == expected
                add('ownership/' + path.parent.name + '/' + path.name, path)
            result_dir = PRIMARY / '.work/strict-warm-build/compiler-cache-retirement-03'
            for name in ['summary.json', 'processes-process.json', 'handles-process.json']:
                add('retirement-03/' + name, result_dir / name)
            add('retirement-03/runner.py', PRIMARY / '.work/retire-completed-compiler-caches-03.py')
            supervisor = PRIMARY / '.work/experiments/compiler-cache-retirement-supervisor-03'
            for name in ['status.json', 'plan.json', 'supervisor.log', 'command.log']:
                add('retirement-03/supervisor/' + name, supervisor / name)
            result = json.loads((result_dir / 'summary.json').read_bytes())
            assert result['status'] == 'passed' and len(result['deleted']) == 9
            assert result['entries_verified'] == 110619 and result['benchmark_commands'] == 0
            assert result['compiler_installation_retained'] and result['retained_files_verified_after']
            assert all(not row['matching'] and row['returncode'] == 0 for row in result['quiescence'].values())
            recommendation = json.loads((ROOT / '.work/cache-retirement-admission-04/recommendations.json').read_bytes())
            selected = next(x for x in recommendation['alternatives'] if x['margin_gib'] == 0.5)
            assert result['paths'] == [x['path'] for x in selected['sequence']]
            for path, expected in result['proof_files'].items():
                assert sha(Path(path).read_bytes()) == expected
            add('packaging/package_evidence.py', Path(__file__).resolve())
            archive = OUT / 'evidence.tar.xz'
            assert not archive.exists()
            with tarfile.open(archive, 'w:xz', preset=3) as tar:
                for name in sorted(members):
                    item = tarfile.TarInfo(name)
                    item.size, item.mode, item.mtime = len(members[name]), 0o644, 0
                    tar.addfile(item, io.BytesIO(members[name]))
            with tarfile.open(archive, 'r:xz') as tar:
                assert tar.getnames() == sorted(members)
                for item in tar:
                    assert item.isfile()
                    assert sha(tar.extractfile(item).read()) == manifest[item.name]['sha256']
            for entry in manifest.values():
                if entry['source'] is not None:
                    assert sha(Path(entry['source']).read_bytes()) == entry['sha256']
            (OUT / 'members.json').write_bytes(encoded(manifest))
            summary = dict(schema_version=1, status='passed', kind='owned generated-cache retirement evidence',
                benchmark_commands=0, performance_claim=False, canonical_lock=str(LOCK),
                inspection_attempts={n: {k: value[k] for k in ['pid', 'started_at', 'finished_at', 'status']}
                    for n, value in attempts.items()},
                inspection_03='unrun, superseded by 04',
                failed_inspection_02=dict(cause='inspect.py shadowed stdlib inspect, recursively acquiring same flock',
                    owned_pid=43063, resolution='exact owned PID revalidated, no children, SIGINT, exit130',
                    peer_process_control=False, receipt_reentry_retained=True),
                retired_roots=result['paths'], entries_revalidated=result['entries_verified'],
                retirement_pid=result['pid'], retirement_finished_at=result['finished_at'],
                free_bytes_before=result['free_bytes_before'], free_bytes_after=result['free_bytes_after'],
                observed_free_bytes_increase=result['free_bytes_after'] - result['free_bytes_before'],
                free_space_caveat='whole-volume observations, not a benchmark or exact exclusive APFS reclamation attribution',
                full_host_ps_lsof_published=False,
                filtered_quiescence='empty candidate matches; raw SHA256, byte/line counts and exit status retained',
                current_user_visibility_only=True,
                protected='source, installations/packages, CI LLVM/stage0 inputs, macro build05, raw results and artifact snapshots',
                archive=dict(path=archive.name, sha256=sha(archive.read_bytes()), bytes=archive.stat().st_size,
                             members=len(manifest), verification='all member hashes and source bytes checked'))
            (OUT / 'summary.json').write_bytes(encoded(summary))
            receipt.update(status='passed', finished_at=time.time(), archive=summary['archive'])
            save()
            (OUT / 'packaging.json').write_bytes(encoded(receipt))
            print(json.dumps(dict(status='passed', pid=os.getpid(), archive=summary['archive'])))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        save()
        raise


if __name__ == '__main__':
    main()

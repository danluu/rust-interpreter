"""Saved runtime evidence predicates; no workload or controller entry point.

The explicit audit runner authenticates these sources and supplies bounded
read-only callbacks. No module import performs an input read or starts work.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
SOURCE = X/'experiments/hir-options-hash/runtime-installation-04'
BASE = dict(path='/Users/danluu/dev/rust-interp-runtime-application-admission-20260918/experiments/hir-options-hash-native-controls-03/inputs.json',
            sha256='8569abb81a61e34b6b5a892116af5218557ceb0436ab8dbf8a31f2aec55b1b1d')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
LIMITS = dict(maximum_files=1024, maximum_file_bytes=64*2**20,
              maximum_logical_bytes=512*2**20, maximum_compressed_bytes=128*2**20,
              maximum_manifest_bytes=4*2**20)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def phase_paths(phase):
    require(phase in ['preflight', 'installation'], 'exact runtime audit phase required')
    return dict(packet=SOURCE/(phase+'-plan-01'),
                work=R/('.work/hir-options-hash-runtime-'+phase+'-04'),
                outer=R/('.work/experiments/hir-options-hash-runtime-'+phase+'-supervisor-04'),
                report=R/('.work/hir-options-hash-runtime-'+phase+'-independent-verification-04.json'))


def owner(plan, launch, terminal, outer, launcher, *, phase, expected, sha, read_json):
    """Bind the original completed owner; never manufacture a passed terminal."""
    paths = phase_paths(phase); packet, work = paths['packet'], paths['work']
    require(plan['phase'] == terminal['phase'] == phase and plan['owner'] == str(R)
            and plan['work'] == str(work) and plan['supervisor_work'] == str(paths['outer']),
            'exact runtime phase/owner paths required')
    require(terminal['status'] == 'passed' and type(terminal['pid']) is int
            and type(terminal['parent_pid']) is int and terminal['pid'] > 0 and terminal['parent_pid'] > 0,
            'actual passed runtime owner required')
    for name in ['application_qualified', 'performance_measurement', 'exporter_qualified', 'std_mir_prepared']:
        require(terminal[name] is False, 'unearned runtime qualification scope')
    require(sha(packet/'launch.json') == expected['launch']
            and terminal['inputs_sha256'] == launch['inputs_sha256'] == expected['inputs'] == sha(packet/'inputs.json')
            and terminal['plan_sha256'] == launch['plan_sha256'] == sha(packet/'plan.json')
            and terminal['snapshot_plan_sha256'] == launch['snapshot_plan_sha256'] == expected['snapshot_plan']
            and sha(packet/'snapshot-plan.json') == expected['snapshot_plan']
            and sha(work/'receipt.json') == expected['receipt'], 'actual packet/terminal association differs')
    require(launch['cwd'] == str(R) and launch['environment'] == plan['launch_environment'] == plan['environment']
            and launch['capacity'] == plan['capacity'] == dict(entry_gib=24, stop_gib=9, floor_gib=8,
                combined_namespace_bytes=14*2**30, evidence_bytes=256*2**20), 'runtime context or limits changed')
    require(outer['status'] == 'finished' and type(outer['returncode']) is int and outer['returncode'] == 0
            and outer['child_pid'] == terminal['pid'] and outer['supervisor_pid'] == terminal['parent_pid']
            and outer['command'] == launch['command'][6:] and outer['cwd'] == str(R)
            and outer['plan_sha256'] == sha(paths['outer']/'plan.json')
            and outer['log_sha256'] == sha(paths['outer']/'command.log'), 'actual runtime supervisor closure differs')
    require(outer['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at']
            <= terminal['finished_at'] <= outer['finished_at']
            and terminal['free_bytes_before'] >= 24*2**30 and terminal['free_bytes_after'] >= 9*2**30,
            'actual runtime admission/timing differs')
    # New launchers must follow the already reviewed actual hash launch schema.
    # Old legacy wrapper-only "finished" records are not relabeled as closure.
    require(launcher['status'] == 'terminal-observed' and type(launcher['returncode']) is int
            and launcher['returncode'] == 0 and type(launcher['launcher_returncode']) is int
            and launcher['launcher_returncode'] == 0 and launcher['outer_sha256'] == sha(paths['outer']/'status.json')
            and launcher['command'] == launch['command'] and launcher['cwd'] == str(R)
            and same(launcher['environment'], launch['environment']) and launcher['launch_sha256'] == expected['launch']
            and launcher['started_at'] <= launcher['launcher_finished_at'] <= launcher['finished_at']
            and outer['finished_at'] <= launcher['terminal_observed_at'] <= launcher['finished_at'],
            'explicit runtime launcher terminal observation required')
    launcher_path = Path(expected['launcher_record'])
    require(sha(launcher_path) == expected['launcher_record_sha256']
            and sha(launcher['launcher_source_path']) == launcher['launcher_source_sha256'],
            'reviewed actual launcher record/source binding differs')
    for stream in ['stdout', 'stderr']:
        require(sha(launcher_path.parent/stream) == launcher[stream+'_sha256'], 'launcher raw differs')
    handoff = read_json(launcher_path.parent/'stdout')
    require(handoff['directory'] == str(paths['outer'])
            and handoff['supervisor_pid'] == outer['supervisor_pid'] == launcher['supervisor_pid']
            and launcher['controller_pid'] == terminal['pid'], 'actual runtime launcher handoff differs')
    return paths


def child_history(plan, terminal, *, desired, read_json, read_bytes, sha):
    """Complete observed process identity allows proven nonoverlapping PID reuse."""
    require(same(plan['children'], desired) and len(terminal['children']) == len(desired),
            'complete exact saved runtime recipe required')
    children, identities, missing = [], [], []
    previous = terminal['admitted_at']
    for index, (wanted, reference) in enumerate(zip(desired, terminal['children'], strict=True)):
        path = Path(wanted['output'])/'receipt.json'; row = read_json(path)
        require(same(reference, dict(path=str(path), sha256=sha(path), pid=row['pid'], returncode=row['returncode']))
                and row['status'] == 'finished' and type(row['returncode']) is int
                and row['returncode'] in wanted['expected'], 'runtime child status/reference differs')
        require(same(row['command'], wanted['argv']) and row['cwd'] == wanted['cwd']
                and same(row['environment'], wanted['environment']) and same(row['expected'], wanted['expected'])
                and row['supervisor_pid'] == terminal['pid'] and row['parent_pid'] == terminal['parent_pid']
                and type(row['pid']) is int and row['pid'] > 0
                and previous <= row['started_at'] <= row['finished_at'] <= terminal['finished_at'],
                'runtime child command/context/owner/timing differs')
        previous = row['finished_at']; observation = row['identity']; fields = observation['ps'].split(None, 9)
        require(observation['ps_returncode'] == 0 and len(fields) == 10
                and list(map(int, fields[:3])) == [row['pid'], terminal['pid'], row['pid']]
                and fields[8] == '??' and fields[9] == ' '.join(wanted['argv']), 'runtime child PS identity differs')
        start = ' '.join(fields[3:8]); time.strptime(start, '%a %b %d %H:%M:%S %Y')
        if observation['cwd_returncode'] == 0:
            require(observation['cwd'].splitlines() == ['p'+str(row['pid']), 'fcwd', 'n'+wanted['cwd']],
                    'runtime child observed cwd differs')
        else:
            require(observation['cwd_returncode'] == 1 and observation['cwd'] == '', 'unexplained unavailable cwd')
            missing.append(dict(index=index, pid=row['pid'], requested_cwd=wanted['cwd'],
                limitation='Fast-child contemporaneous cwd unavailable; recorded cwd is not an observed cwd.'))
        current = dict(index=index, pid=row['pid'], observed_ps_start=start,
                       started_at=row['started_at'], finished_at=row['finished_at'])
        for earlier in identities:
            if earlier['pid'] == current['pid']:
                require(earlier['observed_ps_start'] != start and earlier['finished_at'] <= current['started_at'],
                        'reused PID lacks distinct nonoverlapping observed identity')
        identities.append(current)
        streams = {}
        for stream in ['stdout', 'stderr']:
            streams[stream] = read_bytes(path.parent/stream)
            require(sha(path.parent/stream) == row[stream+'_sha256'], 'runtime child raw hash differs')
        children.append(dict(declaration=copy.deepcopy(wanted), receipt=row, **streams))
    return dict(children=children, identities=identities, unavailable_contemporaneous_cwd=missing)


def controls(*, source, work, audit_path, source_paths, test_paths, read_json, read_bytes, sha, identity):
    """Recheck actual bounded pure controls before loading their selected modules."""
    source, work = Path(source), Path(work)
    freeze = read_json(source/'inputs.json'); terminal = read_json(work/'receipt.json')
    result = read_json(work/'result.json'); audit = read_json(audit_path)
    require(type(freeze['files']) is dict and len(freeze['files']) <= 256, 'bounded control source closure required')
    for name, row in freeze['files'].items():
        stamp = identity(name)
        require([stamp[key] for key in ['dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink']] == row['stamp']
                and sha(name) == row['sha256'], 'actual control frozen file differs')
    for name, target in freeze['routes'].items():
        require(str(Path(name).resolve(strict=True)) == target, 'actual control route differs')
    require(all(str(path) in freeze['files'] for path in [*source_paths, *test_paths]),
            'selected audit source not tested')
    names = []
    for path in test_paths:
        path = Path(path)
        for cls in ast.parse(read_bytes(path), filename=str(path)).body:
            if isinstance(cls, ast.ClassDef):
                names.extend(path.stem+'.'+cls.name+'.'+method.name for method in cls.body
                             if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'))
    require(names and len(names) == len(set(names)) and sorted(names) == freeze['expected_names'] == result['expected_names']
            and sorted(names) == sorted(audit['exact_names']), 'actual source-derived control names differ')
    require(terminal['status'] == result['status'] == 'passed' and audit['status'] == 'verified'
            and type(terminal['controls_passed']) is int and type(result['tests_run']) is int
            and terminal['controls_passed'] == result['tests_run'] == audit['controls'] == len(names)
            and terminal['inputs_sha256'] == sha(source/'inputs.json')
            and terminal['result_sha256'] == audit['result_sha256'] == sha(work/'result.json')
            and audit['receipt_sha256'] == sha(work/'receipt.json'), 'passed actual control proof differs')
    require(all(type(result[key]) is int and result[key] == 0 for key in
                ['failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes', 'child_processes', 'compiler_calls']),
            'control failed or performed unexpected work')
    child_path = work/'command/receipt.json'; child = read_json(child_path)
    require(terminal['commands'] == [dict(path=str(child_path), pid=child['pid'], sha256=sha(child_path))]
            and child['status'] == 'finished' and child['returncode'] == 0
            and child['command'] == freeze['command'] and child['environment'] == freeze['environment']
            and child['supervisor_pid'] == terminal['pid'] and child['parent_pid'] == terminal['parent_pid'],
            'actual control child association differs')
    for stream in ['stdout', 'stderr']:
        require(sha(work/'command'/stream) == child[stream+'_sha256'] == audit['raw_sha256'][stream],
                'actual control raw differs')
    raw = read_bytes(work/'command/stderr').decode('utf-8', 'strict')
    observed = re.findall(r'^test_[A-Za-z0-9_]+ \(([^)]+)\) \.\.\. ok$', raw, re.M)
    require(not read_bytes(work/'command/stdout') and sorted(observed) == sorted(names)
            and re.search(r'^Ran '+str(len(names))+r' tests in [0-9.]+s\n\nOK\n$', raw, re.M),
            'actual control names/footer differ')
    return dict(controls=len(names), receipt_sha256=sha(work/'receipt.json'), result_sha256=sha(work/'result.json'),
                audit=dict(path=str(audit_path), sha256=sha(audit_path)))


def snapshot_readback(*, plan, freeze, packet, work, terminal, snapshot, manifest, lineage,
                      catalog, snapshots, read_json, sha, identity, directory_record, guard):
    """Verify complete logical/physical v2 closure without compression or writes."""
    packet, work = Path(packet), Path(work)
    own = packet/'inputs.json'
    require(same(snapshot['limits'], LIMITS) and snapshot['inputs_sha256'] == sha(own)
            and snapshot['remaining_evidence_reservation_bytes'] == 32*2**20
            and snapshot['evidence_cap_bytes'] == 256*2**20, 'unchanged runtime snapshot policy required')
    require(sha(packet/'snapshot-plan.json') == sha(work/'snapshot-plan.json') == terminal['snapshot_plan_sha256']
            and sha(work/'source-snapshots.json') == terminal['source_snapshots_sha256'], 'actual snapshot document association differs')
    require(same(lineage, plan['snapshot_reuse']), 'complete predecessor snapshot lineage differs')
    names = freeze['snapshot_inputs']
    require(type(names) is list and names == sorted(set(names)) and set(names) <= set(freeze['files']),
            'complete sorted logical selection required')
    records = [dict(path=name, **freeze['files'][name]) for name in names]
    own_identity = identity(own)
    records.append(dict(path=str(own), sha256=sha(own), size=own_identity['size'], identity=own_identity))
    selected = catalog.select(records, lineage)
    require(same(selected, snapshot['reuse_selection']), 'deterministic completed reference selection differs')
    projection = snapshot['projection']
    require(manifest['policy'] == projection['policy'] == 'bounded-gzip-proof-snapshots-v2'
            and same(projection['limits'], LIMITS) and manifest['projection_sha256'] == digest(projection)
            and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,
            'exact verified v2 manifest required')
    expected = {row['path']: row for row in records}
    require(same(projection['files'], expected) and set(manifest['files']) == set(expected)
            and same(manifest['blobs'], projection['blobs']), 'complete logical mapping or blobs differ')
    reuse = {row['blob']['logical_sha256']: row for row in selected['records']}
    require(same(projection['reuse'], reuse) and same(manifest['reuse'], reuse)
            and same(projection['evidence_roots'], selected['evidence_roots'])
            and same(manifest['evidence_roots'], selected['evidence_roots']), 'reused physical owner association differs')
    root = work/'source-snapshots'; root_before = directory_record(root)
    roots = dict(selected['evidence_roots']); roots[str(root)] = root_before['identity']
    sizes = {}; logical = 0
    for name, row in expected.items():
        require(row['size'] <= LIMITS['maximum_file_bytes'] and sha(name) == row['sha256']
                and same(identity(name), row['identity']), 'selected current logical source changed')
        require(row['sha256'] not in sizes or sizes[row['sha256']] == row['size'], 'logical alias size disagreement')
        sizes[row['sha256']] = row['size']; logical += row['size']
    require(set(projection['blobs']) == set(sizes) and len(expected) <= LIMITS['maximum_files']
            and logical == projection['logical_bytes'] <= LIMITS['maximum_logical_bytes']
            and sum(sizes.values()) == projection['unique_logical_bytes'], 'complete bounded logical accounting differs')
    stored = set(); physical = {}; compressed = allocated = new = new_allocated = 0
    for key, blob in projection['blobs'].items():
        require(type(key) is str and re.fullmatch('[a-f0-9]{64}', key)
                and blob['logical_sha256'] == key and blob['logical_bytes'] == sizes[key]
                and blob['filename'] == key+'.gz', 'exact physical blob mapping required')
        if key in reuse:
            reference = reuse[key]
            require(same(blob, reference['blob'])
                    and same(projection['storage'][key], dict(kind='reused', path=reference['path'])),
                    'reused storage declaration differs')
            physical[key] = dict(kind='reused', path=reference['path'])
        else:
            path = root/blob['filename']; stored.add(blob['filename'])
            require(same(projection['storage'][key], dict(kind='stored')), 'new storage declaration differs')
            reference = dict(path=str(path), identity=identity(path), blob=blob, evidence_root=str(root))
            physical[key] = dict(kind='stored', path=str(path))
        snapshots.verify_reference(reference, roots, guard)
        compressed += blob['compressed_bytes']; amount = (blob['compressed_bytes']+4095)//4096*4096
        allocated += amount
        if key not in reuse:
            new += blob['compressed_bytes']; new_allocated += amount
    require(same(manifest['storage'], physical) and set(projection['storage']) == set(physical)
            and root_before['children'] == sorted(stored) and same(directory_record(root), root_before),
            'complete stable new physical membership differs')
    for name, row in expected.items():
        require(same(manifest['files'][name], dict(path=physical[row['sha256']]['path'], sha256=row['sha256'],
                    size=row['size'], encoding='gzip')), 'logical alias omitted or rebound')
    require(compressed == projection['compressed_bytes'] == manifest['compressed_bytes'] <= LIMITS['maximum_compressed_bytes']
            and new == projection['new_compressed_bytes'] == manifest['new_compressed_bytes']
            and compressed-new == projection['reused_compressed_bytes'] == manifest['reused_compressed_bytes']
            and allocated == projection['compressed_allocated_bytes']
            and new_allocated == projection['new_compressed_allocated_bytes'], 'total/new physical byte accounting differs')
    reservation = new_allocated+4096*len(stored)+2*LIMITS['maximum_manifest_bytes']+32*2**20
    admission = terminal['snapshot_admission']
    require(projection['manifest_reservation_bytes'] == 2*LIMITS['maximum_manifest_bytes']
            and reservation == snapshot['projected_reservation_bytes'] == admission['reserved_bytes']
            and snapshot['measured_existing_evidence_bytes']+reservation <= 256*2**20
            and admission['existing_evidence_bytes']+reservation <= 256*2**20, 'actual complete evidence reservation differs')
    return dict(logical_files=len(records), logical_bytes=logical, physical_blobs=len(physical),
                new_physical_blobs=len(stored), reused_physical_blobs=len(reuse), compressed_bytes=compressed,
                new_compressed_bytes=new, projected_reservation_bytes=reservation,
                referenced_physical_paths=sorted({row['path'] for row in physical.values()}),
                full_logical_hashes=True, full_gzip_eof=True)

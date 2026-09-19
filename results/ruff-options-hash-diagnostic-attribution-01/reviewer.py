"""Read only the finite saved diagnostic records; never import task code."""
import collections
import hashlib
import json
import re
import stat
import time
from pathlib import Path

A = Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
REPORT = A / '.work/ruff-options-hash-strict-hir-event-attribution-01.json'
EXPECTED = 'ac1205993b6857afbcde0f7a23ffae2b2861f97944cf631b1e5f0879b0a4801a'
OUT = X / '.work/ruff-options-hash-diagnostic-attribution-independent-review-01.json'
checked = {}
payloads = {}
total = 0


def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size,
            s.st_mtime_ns, s.st_ctime_ns]


def read(path, expected=None):
    global total
    path = str(path)
    if path not in payloads:
        p = Path(path)
        before = p.lstat()
        assert stat.S_ISREG(before.st_mode) and before.st_size <= 8 * 2**20
        total += before.st_size
        assert total <= 48 * 2**20
        data = p.read_bytes()
        assert stamp(before) == stamp(p.lstat()) and len(data) == before.st_size
        checked[path] = dict(path=path, bytes=len(data),
                             sha256=hashlib.sha256(data).hexdigest(), stamp=stamp(before))
        payloads[path] = data
    if expected is not None:
        assert checked[path]['sha256'] == expected
    return payloads[path]


def ref_read(ref, alternate_stamp=False):
    data = read(ref['path'], ref['sha256'])
    assert len(data) == ref['bytes']
    if 'stamp' in ref:
        old = ref['stamp']
        if alternate_stamp:
            old = [old[0], old[1], old[2], old[6], old[3], old[4], old[5]]
        assert checked[ref['path']]['stamp'] == old
    return data


def archive_read(ref):
    old = members[ref['path']]
    assert old['bytes'] == ref['bytes'] and old['sha256'] == ref['sha256']
    data = ref_read(old)
    used_members[ref['path']] = old
    return data


def parse_argv(data):
    parts = data.decode('utf-8').split('\0')
    assert parts[-1] == '' and parts[0] == 'rust-interp-compiler-argv-v1'
    assert parts[1] in ('native', 'exported')
    return parts[1], parts[5:-1]


assert not OUT.exists()
report = json.loads(read(REPORT, EXPECTED))
manifest = json.loads(ref_read(report['archive_manifest'], True))
members = {row['path']: row for row in manifest['members']}
assert len(members) == manifest['member_count'] == 840
used_members = {}
eligibility = json.loads(ref_read(report['original_eligibility_unchanged'], True))
assert eligibility['successful_captures'] == 13491 and eligibility['verified_hits'] == 9877
assert eligibility['performance_qualified'] is False
parser_bytes = ref_read(eligibility['parser_source'])
references = {row['path']: row for row in report['references']}
assert len(references) == len(report['references']) == 381
histories = []
excerpts = []
cold_stream = None
raw_captures = raw_hits = wrapper_count = 0
warm_streams = []

for index, h in enumerate(report['histories']):
    stderr = archive_read(h['stderr'])
    receipt = json.loads(archive_read(h['receipt']))
    assert receipt['status'] == 'finished' and receipt['finished_at'] >= receipt['started_at']
    assert receipt['stderr_sha256'] == h['stderr']['sha256']
    assert receipt['returncode'] == (1 if h['state'] == -1 else 0)
    lines = stderr.decode('utf-8').splitlines()
    running = [i for i, line in enumerate(lines) if re.match(r'\s+Running `', line)]
    top = [i for i in running if ' --crate-name ruff_linter ' in lines[i]]
    assert len(top) == 1
    top = top[0]
    assert top + 1 == h['current_ruff_rustc_line_1based']
    before = [line for line in lines[:top] if line.startswith('[hir-body-capture] ')]
    after = [line for line in lines[top + 1:] if line.startswith('[hir-body-capture] ')]
    hits = [(i, line) for i, line in enumerate(lines) if line.startswith('[hir-body-reuse] ')]
    assert all(' hit cache_hits=1 verify_tree=1 verify_journal=1 verify_poststate=1 ' in s for _, s in hits)
    assert all(i > top for i, _ in hits)
    assert len(before) == 1510
    assert len(after) == (1411 if index == 0 else 0)
    assert len(hits) == (0 if index == 0 else 1411)
    raw_captures += len(before) + len(after)
    raw_hits += len(hits)
    stream = ('\n'.join(before) + '\n').encode()
    assert hashlib.sha256(stream).hexdigest() == h['capture_stream_sha256']
    if index == 0:
        cold_stream = before
    else:
        warm_streams.append(before)
        assert len(running) == 1 and before == cold_stream
    assert len(running) == h['cargo_running_lines']
    fresh_counts = collections.Counter()
    fresh_lines = {}
    last_fresh = None
    for i, line in enumerate(lines[:top]):
        fresh = re.match(r'\s+Fresh (\S+) v', line)
        if fresh:
            last_fresh = fresh[1]
            fresh_lines[last_fresh] = i + 1
        if line.startswith('[hir-body-capture] ') and index:
            assert last_fresh is not None
            fresh_counts[last_fresh] += 1
    if index:
        assert dict(fresh_counts) == h['fresh_dependency_event_counts']
    record_dir = Path(h['current_argv_record']['path']).parent
    rows = [row for row in manifest['members'] if Path(row['path']).parent == record_dir]
    assert {p.name for p in record_dir.iterdir()} == {Path(row['path']).name for row in rows}
    assert len(rows) == h['actual_wrapper_records'] == (313 if index == 0 else 6)
    roles = collections.Counter()
    native_probes = []
    for row in rows:
        kind, argv = parse_argv(archive_read(row))
        roles[kind] += 1
        assert row['path'] in references
        ref_read(references[row['path']], True)
        if kind == 'exported':
            assert row['path'] == h['current_argv_record']['path']
            assert argv[argv.index('--crate-name') + 1] == 'ruff_linter'
            assert all(flag in argv for flag in ('-Zhir-body-cache-capture=true', '-Zhir-body-cache-reuse=true', '-Zincremental-info=true'))
            assert any(arg.startswith('incremental=') and argv[i - 1] == '-C' for i, arg in enumerate(argv))
        elif index:
            assert '-vV' in argv or '--print=file-names' in argv
            native_probes.append(dict(path=row['path'], version='-vV' in argv,
                                      print_file_names='--print=file-names' in argv))
    assert dict(roles) == h['wrapper_record_roles']
    wrapper_count += len(rows)
    capture_locations = [i for i, s in enumerate(lines[:top]) if s.startswith('[hir-body-capture] ')]
    assert capture_locations[-1] + 1 == h['last_dependency_capture_line_1based']
    assert (hits[0][0] + 1 if hits else None) == h['first_current_hit_line_1based']
    selected = {top - 1, top, top + 1, top + 2}
    selected.update(capture_locations[:1] + capture_locations[-1:])
    selected.update(i - 1 for i in capture_locations[:1])
    if hits:
        selected.update([hits[0][0], hits[-1][0]])
    excerpts.append(dict(label=h['label'], source=h['stderr'],
                         lines=[dict(line=i + 1, text=lines[i]) for i in sorted(selected) if 0 <= i < len(lines)]))
    histories.append(dict(label=h['label'], state=h['state'], returncode=receipt['returncode'],
                          cargo_running_lines=len(running), top_running_line=top + 1,
                          wrapper_records=len(rows), roles=dict(roles), native_probes=native_probes,
                          fresh_dependency_counts=dict(fresh_counts), fresh_source_lines=fresh_lines,
                          initial_dependency_captures=len(before) if index == 0 else 0,
                          replayed_dependency_captures=len(before) if index else 0,
                          current_ruff_captures=len(after), current_ruff_hits=len(hits),
                          dependency_stream_sha256=hashlib.sha256(stream).hexdigest()))

assert len(histories) == 8 and len(warm_streams) == 7 and wrapper_count == 355
baseline_count = 0
for row in eligibility['per_command']:
    if row['mode'] == 'baseline':
        data = archive_read(row['stderr'])
        assert not any(line.startswith((b'[hir-body-capture] ', b'[hir-body-reuse] ')) for line in data.splitlines())
        baseline_count += 1
assert baseline_count == 8
assert raw_captures == 13491 == 1510 + 1411 + 7 * 1510
assert raw_hits == 9877 == 7 * 1411
assert report['summary'] == dict(actual_cold_candidate_capture_events=2921,
    actual_initial_dependency_captures=1510, actual_initial_ruff_captures=1411,
    actual_warm_ruff_capture_events=0, actual_warm_ruff_hits_per_history=1411,
    actual_warm_ruff_hits_total=9877, mechanism_eligibility_preserved=True,
    off_arm_messages=0, raw_capture_messages=13491, warm_histories=7,
    warm_replayed_dependency_capture_messages=10570)
for path, row in checked.items():
    assert stamp(Path(path).lstat()) == row['stamp']

review = dict(status='verified-corrective-diagnostic-attribution', checked_at=time.time(),
    attribution_report=checked[str(REPORT)], old_eligibility=checked[report['original_eligibility_unchanged']['path']],
    archive_manifest=checked[report['archive_manifest']['path']],
    existing_archive=manifest['files']['evidence.tar.gz'],
    scope='Saved argv, exact literal message streams, Fresh/Running order, original parser source and raw-count arithmetic; no compiler, benchmark, provider probes or timing qualification.',
    not_reviewed='Older profile timing attribution and the separate unmeasured single-walk optimization hypothesis in A report are outside this corrective event-count review.',
    result=report['summary'], histories=histories, excerpts=excerpts,
    initial_dependency_and_all_warm_streams_byte_identical=True,
    actual_wrapper_records=355, off_arm_histories=baseline_count,
    historical_wrong_edit_returncode=1, current_performance_claim=False,
    archive_members_checked=list(used_members.values()), checked_files=list(checked.values()),
    checked_bytes=total, reviewer_source=dict(path=__file__, sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
    preservation='Original 065d eligibility report and all original records remain byte-for-byte unchanged; its successful_captures=13491 is a raw message count, not 13491 distinct executed captures.')
with OUT.open('x') as output:
    json.dump(review, output, indent=2, sort_keys=True)
    output.write('\n')
print(json.dumps(dict(path=str(OUT), sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
                     bytes=OUT.stat().st_size, checked_files=len(checked), checked_bytes=total,
                     archive_members=len(used_members), result=report['summary']), sort_keys=True))

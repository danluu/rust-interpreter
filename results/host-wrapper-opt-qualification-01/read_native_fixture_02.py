"""Finite saved-only native fixture readback. Never import target code."""
from pathlib import Path
import hashlib
import json
import os
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = ROOT / 'experiments/host-wrapper-opt-fixture-02'
OUT = ROOT / 'results/host-wrapper-opt-fixture-02'
WORK = ROOT / '.work/host-wrapper-opt-fixture-02'
HOST = 'aarch64-apple-darwin'
checked = {}


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def read(path, expected=None):
    path = Path(path)
    before = stamp(path)
    assert stat.S_ISREG(before[2]) and before[4] <= 8 * 2**20
    data = path.read_bytes()
    assert before == stamp(path)
    row = dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), identity=before)
    if expected is not None:
        if isinstance(expected, str):
            assert row['sha256'] == expected
        else:
            for key in ('path', 'sha256', 'bytes', 'identity'):
                if key in expected:
                    assert row[key] == expected[key], (path, key)
    checked[str(path)] = row
    return data


def document(path, expected=None):
    return json.loads(read(path, expected))


def option(argv, key):
    values = [argv[i+1] if a == key else a[len(key)+1:]
              for i, a in enumerate(argv) if a == key or a.startswith(key + '=')]
    assert len(values) <= 1
    return values[0] if values else None


def codegen(argv):
    values = [argv[i+1] if a == '-C' else a[2:]
              for i, a in enumerate(argv) if a == '-C' or a.startswith('-C')]
    result = {}
    for value in values:
        key, sep, val = value.partition('=')
        key = key.replace('_', '-')
        assert key not in result
        assert sep or key == 'prefer-dynamic'
        result[key] = val if sep else 'yes'
    return result


def closed_parent(number, expected_rc):
    p = ROOT / f'.work/host-wrapper-opt-fixture-execution-{number}/record.json'
    row = document(p)
    assert row['status'] == 'finished' and row['returncode'] == expected_rc
    assert row['child_may_be_live'] is False and row['signals'] == row['retries'] == 0
    assert row['started_at'] < row['finished_at']
    read(row['source']['path'], row['source']['sha256'])
    for kind in ('stdout', 'stderr'):
        read(p.parent / kind, row[kind + '_sha256'])
    rec = document(ROOT / f'results/host-wrapper-opt-fixture-{number}/record.json')
    assert rec['pid'] == row['child_pid'] and rec['parent_pid'] == row['parent_pid']
    assert row['command'][2:] == rec['argv']
    assert row['started_at'] <= rec['started_at'] < rec['finished_at'] <= row['finished_at']
    assert rec['status'] == ('passed' if expected_rc == 0 else 'failed')
    return row, rec


def main():
    parent, rec = closed_parent('02', 0)
    old_parent, old_rec = closed_parent('01', 1)
    assert old_rec['error'] == "RuntimeError('owned actual extern')"
    assert not (ROOT / 'results/host-wrapper-opt-fixture-01/cargo-on').exists()
    assert not (ROOT / 'results/host-wrapper-opt-fixture-01/result.json').exists()
    binding = document(H / 'binding.json', '001fbd0522facab8eb2423ca534b434177e4076f38d14ffd771ea08ed8dcf370')
    result = document(OUT / 'result.json', rec['result'])
    assert result['status'] == 'passed'
    assert all(result[k] is False for k in ('benchmark', 'performance_qualified', 'bytecode_qualified'))
    before = document(OUT / 'source-before.json')
    after = document(OUT / 'source-after.json')
    assert before == after and len(before) == len(binding['sources']) == 367
    deferred_provider_count = 0
    for path, row in before.items():
        assert row['sha256'] == binding['sources'][path]
        if '/beta-sysroot/' in path:
            deferred_provider_count += 1
        else:
            read(path, row)
    assert deferred_provider_count == 335
    tool_before = document(OUT / 'tools-before.json')
    assert tool_before == document(OUT / 'tools-after.json') and len(tool_before) == 5
    assert {p: r['sha256'] for p, r in tool_before.items()} == binding['tools']
    # Physical provider/tool bytes were fully read by the producer before/after.
    # This reader authenticates its receipts without repeating those large reads.
    read(result['wrapper']['path'], result['wrapper']['sha256'])
    copied = document(OUT / 'fixture-after.json')
    for p, row in copied.items():
        content = read(p, row)
        original = ROOT / 'experiments/host-build-opt-01/qualification-fixture' / Path(p).relative_to(WORK / 'fixture')
        assert content == read(original)
    labels = ['build-wrapper', 'wrapper-roles', 'wrapper-policy', 'cargo-version',
              'runtime-version', 'build-version', 'cargo-off', 'cargo-on']
    closures = []
    streams = {}
    last = rec['started_at']
    for label in labels:
        directory = OUT / label
        assert {p.name for p in directory.iterdir()} == {'record.json', 'observation.json', 'stdout', 'stderr'}
        command = document(directory / 'record.json')
        observation = document(directory / 'observation.json')
        assert command['status'] == 'finished' and command['returncode'] == 0
        assert command['parent_pid'] == rec['pid'] and command['cwd'] == str(WORK / 'fixture')
        assert last <= command['started_at'] < command['finished_at'] <= rec['finished_at']
        last = command['finished_at']
        assert not observation['violations'] and observation['retained_normal_wait']
        assert not observation['atomic_disk_quota'] and not observation['hard_wall_limit']
        assert max(observation['sampled_peak'].values()) <= 256 * 2**20
        streams[label] = tuple(read(directory / name).decode() for name in ('stdout', 'stderr'))
        closures.append(dict(label=label, pid=command['pid'], parent_pid=command['parent_pid'],
                             started_at=command['started_at'], finished_at=command['finished_at']))
    roles = binding['compiler_roles']
    assert json.loads(streams['wrapper-roles'][0]) == roles
    cap = streams['wrapper-policy'][0].splitlines()
    assert len(cap) == 3 and json.loads(cap[0]) == binding['capability']
    assert cap[1] == roles['runtime']['default_sysroot'] and json.loads(cap[2]) == roles
    for label, expected in [('cargo', binding['cargo_version']), ('runtime', roles['runtime']['verbose_version']),
                            ('build', roles['build']['verbose_version'])]:
        assert streams[label + '-version'][0] == expected
    assert [arm['mode'] for arm in result['arms']] == ['off', 'on']
    totals = dict(compiles=0, queries=0, calls=0, profiles=0)
    normalized = []
    normalized_profiles = []
    for arm in result['arms']:
        mode = arm['mode']
        assert len(arm['calls']) == 11 and len(arm['build_scripts']) == 4
        assert 'test result: ok. 1 passed; 0 failed;' in streams['cargo-' + mode][0]
        assert {p.name for p in (WORK / ('trace-' + mode)).iterdir()} == {Path(r['original']['path']).name for r in arm['calls']}
        assert {p.name for p in (WORK / ('final-' + mode)).iterdir()} == {Path(r['final']['path']).name for r in arm['calls']}
        norm = []
        for row in arm['calls']:
            original = document(row['original']['path'], row['original'])
            final = read(row['final']['path'], row['final']).decode().split('\0')
            argv = original['argv']
            args = argv[1:]
            assert argv == row['argv'] and argv[0] == roles['runtime']['executable']['path']
            assert Path(row['final']['path']).name == f"native-{original['pid']}.argv"
            assert final[:4] == ['rust-interp-compiler-argv-v1', 'native', roles['runtime']['default_sysroot'], original['cwd']]
            assert final[-1] == '' and original['environment']['RUST_INTERP_HOST_CODEGEN_OPT'] == mode
            assert not any(k.startswith('CARGO_PROFILE_') for k in original['environment'])
            query = not any(a.endswith('.rs') for a in args)
            target = option(args, '--target')
            assert target in (None, HOST)
            kinds = [args[i+1] if a == '--crate-type' else a.partition('=')[2]
                     for i, a in enumerate(args) if a == '--crate-type' or a.startswith('--crate-type=')]
            library = any(t in ('lib', 'rlib') for k in kinds for t in k.split(','))
            emit = option(args, '--emit')
            eligible = not query and target is None and '--test' not in args and emit is not None and 'link' in emit.split(',') and (library or kinds == ['proc-macro'])
            assert row['query'] == query and row['host'] == (target is None) and row['eligible'] == eligible
            cg = codegen(args)
            expected = argv + ['-Zstable-cgu-partitioning=no']
            if target is not None:
                expected += ['--sysroot', roles['runtime']['default_sysroot']]
            if library:
                expected += ['-Zalways-encode-mir=yes']
            if mode == 'on' and eligible:
                expected += ['-Copt-level=3', '-Zmir-opt-level=1', '-Clto=off']
                if 'debug-assertions' not in cg:
                    expected += ['-Cdebug-assertions=yes']
                if 'overflow-checks' not in cg:
                    expected += ['-Coverflow-checks=' + ('no' if cg.get('debug-assertions') in ('no', 'false', 'off', 'n') else 'yes')]
            assert final[4:-1] == expected
            final_cg = codegen(final[5:-1])
            assert cg == row['original_codegen'] and final_cg == row['final_codegen']
            if not query:
                opt = final_cg.get('opt-level', '0')
                assert opt == ('1' if target else '3' if mode == 'on' and eligible else '0')
                debug = final_cg.get('debug-assertions', 'yes' if opt == '0' else 'no')
                assert debug in ('yes', 'true', 'on', 'y') and final_cg.get('overflow-checks', debug) in ('yes', 'true', 'on', 'y')
            for ext in row['externs']:
                if ext['artifact'] is None:
                    assert ext == dict(name='proc_macro', artifact=None, source='bound-runtime-sysroot') and kinds == ['proc-macro'] and target is None
                else:
                    assert Path(ext['artifact']['path']).is_relative_to(WORK / ('target-' + mode))
                    read(ext['artifact']['path'], ext['artifact'])
            totals['calls'] += 1
            totals['queries' if query else 'compiles'] += 1
            norm.append(json.dumps([a.replace(str(WORK / ('target-' + mode)), '<target>') for a in argv]))
        assert sum(r['eligible'] for r in arm['calls']) == 2
        assert {(r['crate'], r['host'], r['test']) for r in arm['calls'] if not r['query'] and r['crate'] != 'build_script_build'} == {
            ('profile_shared_fixture', True, False), ('profile_shared_fixture', False, False),
            ('profile_host_fixture', True, False), ('profile_target_fixture', False, True)}
        scripts = [r for r in arm['calls'] if r['crate'] == 'build_script_build']
        assert len(scripts) == 3 and all(r['host'] and not r['test'] and not r['eligible'] for r in scripts)
        assert {r['package'] for r in scripts} == {'profile-host-fixture', 'profile-shared-fixture', 'profile-target-fixture'}
        profile_norm = []
        events = [json.loads(line) for line in streams['cargo-' + mode][0].splitlines() if line.startswith('{')]
        event_paths = {str(Path(e['out_dir']) / 'profile.json') for e in events if e.get('reason') == 'build-script-executed'}
        assert event_paths == {p['source']['path'] for p in arm['build_scripts']}
        for p in arm['build_scripts']:
            value = document(p['source']['path'], p['source'])
            assert value == p['value'] and value['debug'] == 'true'
            assert value['opt_level'] == ('1' if p['target'] else '0')
            profile_norm.append(json.dumps([p['target'], value], sort_keys=True))
            totals['profiles'] += 1
        normalized.append(sorted(norm))
        normalized_profiles.append(sorted(profile_norm))
    assert normalized[0] == normalized[1] and normalized_profiles[0] == normalized_profiles[1]
    assert totals == dict(compiles=14, queries=8, calls=22, profiles=8)
    # Preserve exact failed01 child closure and all its seven command raw records.
    old_out = ROOT / 'results/host-wrapper-opt-fixture-01'
    for label in labels[:-1]:
        old = document(old_out / label / 'record.json')
        assert old['status'] == 'finished' and old['returncode'] == 0 and old['parent_pid'] == old_rec['pid']
        assert old_rec['started_at'] <= old['started_at'] < old['finished_at'] <= old_rec['finished_at']
        for name in ('stdout', 'stderr', 'observation.json'):
            read(old_out / label / name)
    read(__file__)
    report = dict(status='verified', scope='Native fixture02 correctness only; no timings, RBC or full exporter qualification.',
        pid=os.getpid(), parent_pid=os.getppid(), finished_at=time.time(), result=checked[str(OUT / 'result.json')],
        normal_parent=parent, commands=closures, totals=totals, immutable_source_rows=367,
        source_payloads_rehashed=32, provider_rows_authenticated_before_after_without_rehash=335,
        tool_receipts_before_after_equal=5, provider_tool_payloads_rehashed=0,
        exact_normalized_original_argv_equal=True, checks_and_Cargo_profiles_equal=True,
        failed01=dict(parent=old_parent, failure=old_rec['error'], closed_successful_children=7, on_arm_ran=False),
        producer_reported_footprint=result['footprint'], checked_files=checked)
    dest = X / '.work/host-wrapper-opt-native-fixture02-independent-readback-01.json'
    payload = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    dest.open('xb').write(payload)
    print(json.dumps(dict(path=str(dest), sha256=hashlib.sha256(payload).hexdigest(), files=len(checked), bytes=len(payload))))


if __name__ == '__main__':
    main()

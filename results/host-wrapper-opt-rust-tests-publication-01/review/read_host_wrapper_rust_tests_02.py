"""Finite saved-only readback; no task imports, compiler or provider probes."""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H = ROOT/'experiments/host-wrapper-opt-rust-tests-02'
OUT = ROOT/'results/host-wrapper-opt-rust-tests-02'
WORK = ROOT/'.work/host-wrapper-opt-rust-tests-02'
PARENT = ROOT/'.work/host-wrapper-opt-rust-tests-execution-02'
checked = {}


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def read(path, want=None):
    path = Path(path)
    before = stamp(path)
    assert stat.S_ISREG(before[2]) and before[4] < 8 * 2**20
    data = path.read_bytes()
    assert stamp(path) == before
    row = dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), identity=before)
    if isinstance(want, str):
        assert row['sha256'] == want
    elif want is not None:
        assert all(row[k] == v for k, v in want.items())
    checked[str(path)] = row
    return data


def doc(path, want=None):
    return json.loads(read(path, want))


def main():
    parent = doc(PARENT/'record.json', '403b449b041cc82a78a61aff664c1355467374661150b3291a3763edbbd941f4')
    assert parent['status'] == 'finished' and parent['returncode'] == 0
    assert parent['child_may_be_live'] is False and parent['signals'] == parent['retries'] == 0
    assert parent['qualification_verified'] is True
    read(parent['source']['path'], parent['source']['sha256'])
    for name in ('stdout', 'stderr'):
        assert not read(PARENT/name, parent[name+'_sha256'])
    rec = doc(OUT/'record.json', parent['receipt']['sha256'])
    assert rec['status'] == 'passed' and rec['pid'] == parent['child_pid'] == 13750
    assert rec['parent_pid'] == parent['parent_pid'] == 12399
    assert parent['command'][2:] == rec['argv']
    assert parent['started_at'] <= rec['started_at'] < rec['finished_at'] <= parent['finished_at']
    binding = doc(H/'binding.json', '7d60a8dcf6024195ac8ec7d8a2d715d7754b061d9c33ed40b73f4fa8ea43baef')
    before = doc(OUT/'source-before.json')
    assert before == doc(OUT/'source-after.json') and len(before) == 355
    assert set(before) == set(binding['sources'])
    provider_count = 0
    for p, row in before.items():
        assert row['sha256'] == binding['sources'][p] and stamp(p) == row['identity']
        if '/beta-sysroot/' in p:
            provider_count += 1
        else:
            read(p, row)
    assert provider_count == 335
    tools = doc(OUT/'tools-before.json')
    assert tools == doc(OUT/'tools-after.json') and len(tools) == 2
    assert {p: row['sha256'] for p, row in tools.items()} == binding['tools']
    for p, row in tools.items():
        assert stamp(p) == row['identity']
    result = doc(OUT/'result.json', rec['result'])
    assert result['status'] == 'passed' and result['commands'] == 8 and result['tests'] == 43
    for key in ('benchmark', 'bytecode_qualified', 'full_exporter_qualified', 'compiler_roles_cargo_suite_run'):
        assert result[key] is False
    assert max(result['footprint'][k] for k in ('logical_bytes', 'allocated_bytes')) <= 256*2**20
    order = ['host_codegen', 'host_library', 'host_proc_macro', 'wrapper_route']
    assert [s['crate'] for s in result['suites']] == order
    roles = binding['compiler_roles']
    closures = []
    actual_names = {}
    last = rec['started_at']
    for name, suite in zip(order, result['suites']):
        source = binding['tests'][name]
        text = read(source['source'], source['sha256']).decode()
        expected_names = sorted(re.findall(r'#\[test\]\s*fn\s+(\w+)\s*\(', text))
        assert expected_names == source['names'] and '#[ignore' not in text
        executable = WORK/'bin'/name
        read(executable, suite['executable'])
        commands = [
            [roles['build']['executable']['path'], '--edition=2024', '--test', '--crate-name', name,
             *roles['build_rustflags'], '-Copt-level=0', '-Cdebuginfo=0', source['source'], '-o', str(executable)],
            [str(executable), '--test-threads=1'],
        ]
        for kind, argv in zip(('compile', 'test'), commands):
            d = OUT/(kind+'-'+name)
            assert {p.name for p in d.iterdir()} == {'record.json', 'observation.json', 'stdout', 'stderr'}
            row = doc(d/'record.json')
            assert row['command'] == argv and row['cwd'] == str(WORK/'fixture')
            assert row['status'] == 'finished' and row['returncode'] == 0 and row['parent_pid'] == rec['pid']
            assert last <= row['started_at'] < row['finished_at'] <= rec['finished_at']
            last = row['finished_at']
            assert row['environment']['TMPDIR'] == str(WORK/'tmp')
            assert row['environment']['RUST_INTERP_RUSTC_COMMIT'] == roles['runtime_source_commit']
            observation = doc(d/'observation.json')
            assert not observation['violations'] and observation['retained_normal_wait']
            assert not observation['hard_wall_limit'] and not observation['atomic_disk_quota']
            assert max(observation['sampled_peak'].values()) <= 256*2**20
            stdout, stderr = [read(d/k).decode() for k in ('stdout', 'stderr')]
            if kind == 'test':
                assert not stderr
                names = re.findall(r'^test ([A-Za-z0-9_:]+) \.\.\. ok$', stdout, re.M)
                assert sorted(names) == expected_names and names == suite['names']
                assert len(names) == len(set(names))
                assert f'test result: ok. {len(names)} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;' in stdout
                actual_names[name] = names
            closures.append(row)
    assert sum(len(v) for v in actual_names.values()) == 43
    for ref in binding['failed_predecessor'].values():
        read(ref['path'], ref)
    assert not list((WORK/'tmp').iterdir())
    read(__file__)
    report = dict(status='verified', scope='Four direct std-only Rust test suites; no Cargo/full exporter/RBC/performance qualification.',
        pid=os.getpid(), parent_pid=os.getppid(), finished_at=time.time(), actual_parent=parent,
        result=checked[str(OUT/'result.json')], actual_commands=closures, actual_names=actual_names,
        tests=43, commands=8, source_rows=355, full_source_tables_before_after_equal=True,
        current_nonprovider_sources_rehashed=20, current_provider_source_stamps=335, provider_payloads_rehashed=0,
        tool_tables_before_after_equal=True, current_tool_stamps=2, tool_payloads_rehashed=0,
        failure01_preserved=binding['failed_predecessor'], production_sources_unchanged=True,
        footprint=result['footprint'], checked_files=checked)
    dest = X/'.work/host-wrapper-opt-rust-tests02-independent-readback-01.json'
    payload = (json.dumps(report, sort_keys=True, indent=2)+'\n').encode()
    dest.open('xb').write(payload)
    print(json.dumps(dict(path=str(dest), sha256=hashlib.sha256(payload).hexdigest(), files=len(checked), bytes=len(payload))))


if __name__ == '__main__':
    main()

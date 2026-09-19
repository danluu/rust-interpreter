"""Finite source/raw publication of failed01 and passed02; no payload walks."""
from pathlib import Path
import hashlib
import json
import os
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
DEST = ROOT/'results/host-wrapper-opt-rust-tests-publication-01'
LIMIT = 2 * 2**20


def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def read(path):
    path = Path(path)
    before = stamp(path)
    assert stat.S_ISREG(before[2]) and before[4] < LIMIT
    data = path.read_bytes()
    assert stamp(path) == before and len(data) == before[4]
    return data, dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), identity=before)


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(data)


def main():
    assert not DEST.exists()
    selections = {}
    def add(path, relative):
        assert relative not in selections and '..' not in Path(relative).parts
        selections[relative] = Path(path)
    suite_names = ('host_codegen','host_library','host_proc_macro','wrapper_route')
    for number in ('01','02'):
        source = ROOT/f'experiments/host-wrapper-opt-rust-tests-{number}'
        for name in ('run.py','binding.json','README.md'):
            add(source/name, f'source/{number}/{name}')
        diff = 'run.py.from-native-fixture02.diff' if number == '01' else 'run.py.from-failed01.diff'
        add(source/diff, f'source/{number}/{diff}')
        if number == '02':
            for name in ('host_codegen.rs','host_codegen.rs.from-failed01.diff'):
                add(source/'tests'/name, f'source/{number}/tests/{name}')
        parent = X/f'.work/execute_host_wrapper_opt_rust_tests_{number}.py'
        add(parent, f'parents/{number}/{parent.name}')
        suffix = '.from-native02.diff' if number == '01' else '.from-failed01.diff'
        add(Path(str(parent)+suffix), f'parents/{number}/{parent.name}{suffix}')
        execution = ROOT/f'.work/host-wrapper-opt-rust-tests-execution-{number}'
        assert {p.name for p in execution.iterdir()} == {'record.json','stdout','stderr'}
        for name in ('record.json','stdout','stderr'):
            add(execution/name, f'execution/{number}/{name}')
        result = ROOT/f'results/host-wrapper-opt-rust-tests-{number}'
        top = ['record.json','source-before.json','tools-before.json']
        if number == '02':
            top += ['result.json','source-after.json','tools-after.json']
        suites = ('host_codegen',) if number == '01' else suite_names
        labels = [kind+'-'+name for name in suites for kind in ('compile','test')]
        assert {p.name for p in result.iterdir()} == set(top+labels)
        for name in top:
            add(result/name, f'actual/{number}/{name}')
        for label in labels:
            assert {p.name for p in (result/label).iterdir()} == {'record.json','observation.json','stdout','stderr'}
            for name in ('record.json','observation.json','stdout','stderr'):
                add(result/label/name, f'actual/{number}/{label}/{name}')
    wrapper = ROOT/'experiments/host-wrapper-opt-01'
    for name in suite_names:
        add(wrapper/f'crates/mir-export/tests/{name}.rs', f'source/original/tests/{name}.rs')
    for name in ('wrapper_route.rs','host_proc_macro.rs'):
        add(wrapper/'crates/mir-export/src'/name, 'source/original/src/'+name)
    add(wrapper/'wrapper-sources.json', 'source/original/wrapper-sources.json')
    add(ROOT/'experiments/host-build-opt-01/qualify-fixture-02.py', 'source/utilities/qualify-fixture-02.py')
    add(Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/scripts/workflow_io.py'), 'source/utilities/workflow_io.py')
    review_names = [
        'host-wrapper-opt-rust-tests-source-handoff-01.json',
        'host-wrapper-opt-rust-tests01-failure-readback-01.json',
        'host-wrapper-opt-rust-tests02-source-handoff-01.json',
        'host-wrapper-opt-rust-tests02-independent-readback-01.json',
        'read_host_wrapper_rust_tests_02.py',
    ]
    for name in review_names:
        add(X/'.work'/name, 'review/'+name)
    add(O/'.work/host-wrapper-rust-tests-module-source-review-01.json', 'review/host-wrapper-rust-tests-module-source-review-01.json')
    add(Path(__file__), 'review/'+Path(__file__).name)
    frozen = {}
    total = 0
    for relative,path in selections.items():
        data,row = read(path)
        frozen[relative] = dict(source=row, data=data)
        total += len(data)
    assert len(frozen) < 120 and total < LIMIT
    final_review = json.loads(frozen['review/host-wrapper-opt-rust-tests02-independent-readback-01.json']['data'])
    assert final_review['status'] == 'verified' and final_review['tests'] == 43 and final_review['commands'] == 8
    assert frozen['review/host-wrapper-opt-rust-tests02-independent-readback-01.json']['source']['sha256'] == '18efebba05ebe62b0cd64586313c610df8f1700e8c15b89d152fea5fe6ffd0fa'
    failure = json.loads(frozen['review/host-wrapper-opt-rust-tests01-failure-readback-01.json']['data'])
    assert failure['status'] == 'verified-closed-test-failure'
    assert frozen['review/host-wrapper-opt-rust-tests01-failure-readback-01.json']['source']['sha256'] == '2f7cebfa56ffbbe19284ca94307a60ca69f24a60e76ca27cc9f7e66f4c6b1c9a'
    binding = json.loads(frozen['source/02/binding.json']['data'])
    external = dict(status='external-payloads-not-copied',
        compiler_source_rows={p:sha for p,sha in binding['sources'].items() if '/beta-sysroot/' in p},
        tool_files=binding['tools'], fixture_binding=binding['fixture_binding'],
        earlier_native_qualification=binding['prerequisites'],
        test_binaries='Exact paths/SHA/stamps remain in actual02/result and readback; bytes excluded.',
        scope='No provider, runtime, source tree or target tree walk/copy. No payload retirement.')
    readme = '''# Direct Rust test qualification

Attempt01 compiled host_codegen successfully, then closed with five passed cases and one failed legacy-O1 case. That test cleared compiler_rustc while retaining stable_cgu_partitioning=off, so the existing guard rejected its incomplete context. The other three suites did not run. Its exact source, initial input table, command output and closed parent/controller records remain preserved.

Attempt02 changes only that test context by clearing stable_cgu_partitioning as well, and uses an explicit path to the unchanged original production module. Fresh output routes preserve attempt01. All 43 cases passed: 6 host_codegen, 6 host_library, 6 host_proc_macro, and 25 wrapper_route. Four direct D2/B3 compilations and four single-threaded native test executions closed normally. Exact names, full stdout/stderr, command environments, source bindings and parent/child records are retained.

These are std-only routing tests. No Cargo compiler_roles integration suite, full exporter, bytecode workload or performance measurement is qualified. The native Cargo fixture02 is an earlier separate qualification referenced by its actual hashes. Source handoffs and bindings retain their historical unrun status; actual result records establish what subsequently ran.

The successful producer fully read all 355 declared source rows and both build tools before/after. The independent saved reader authenticated those equal tables, rehashed 20 nonprovider sources and checked current stamps for 335 B3 entries and two tools; it did not repeat provider/tool payload reads. The failed attempt has no full after-table, and its readback states that limit explicitly. No test-binary/provider payload is duplicated here. There were no signals or automatic retries; fixed resource thresholds remain observational, not atomic reservations.
'''
    DEST.mkdir()
    manifest_files = {}
    for relative,value in frozen.items():
        write(DEST/relative,value['data'])
        manifest_files[relative] = value['source']
    generated = {'README.md':readme.encode(), 'external-references.json':encode(external)}
    for name,data in generated.items():
        write(DEST/name,data)
        manifest_files[name] = dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),source='publication-generated')
    manifest = dict(status='closed-failure01-and-success02',policy='finite-rust-test-source-raw-publication-v1',
        files=manifest_files, original_payload_files=len(frozen), tests02=43, actual02_commands=8,
        benchmark=False, full_exporter_qualified=False, payload_bytes=sum(v['bytes'] for v in manifest_files.values()))
    write(DEST/'manifest.json',encode(manifest))
    copied = {}
    for relative,row in manifest_files.items():
        data,current = read(DEST/relative)
        assert current['sha256'] == row['sha256'] and current['bytes'] == row['bytes']
        copied[relative] = current
    for relative,value in frozen.items():
        data,current = read(value['source']['path'])
        assert current == value['source'] and data == value['data']
    readback = dict(status='verified',pid=os.getpid(),parent_pid=os.getppid(),finished_at=time.time(),
        manifest=read(DEST/'manifest.json')[1], full_copied_EOF_hashes_verified=len(copied),
        original_current_bytes_and_stamps_equal=True, payloads=copied)
    write(DEST/'READBACK.json',encode(readback))
    stages = [str(p.relative_to(ROOT)) for p in sorted(DEST.rglob('*')) if p.is_file()]
    stages.append(str((DEST/'STAGE.json').relative_to(ROOT)))
    write(DEST/'STAGE.json',encode(dict(paths=stages,git_operations_performed=False)))
    complete = [p for p in DEST.rglob('*') if p.is_file()]
    assert len(complete) <= 128 and sum(p.stat().st_size for p in complete) <= LIMIT
    print(json.dumps(dict(path=str(DEST),files=len(complete),bytes=sum(p.stat().st_size for p in complete),
        manifest=read(DEST/'manifest.json')[1],readback=read(DEST/'READBACK.json')[1],stage=read(DEST/'STAGE.json')[1])))


if __name__ == '__main__':
    main()

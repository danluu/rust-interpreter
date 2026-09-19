"""Unrun one-shot stock/Arena04 real-compiler fixture; no retries or signals."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import resource
import shutil
import stat
import subprocess
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE = ROOT/'experiments/proc-macro-arena-compiler-02'
WORK = ROOT/'.work/proc-macro-arena-compiler-02'
OUT = ROOT/'results/proc-macro-arena-compiler-02'
TC = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin')
BRIDGE = ROOT/'.work/proc-macro-arena-bridge-01'
OLD = ROOT/'results/proc-macro-arena-bridge-01'
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PLAN_SHA = '3bad7581c919150e11a5b13be9be99508768856886510140378cc62a3f157a2c'
OLD_SOURCE_SHA = '16ceacc4a5c86604ed06dc291b5f78a49b34283f607b5e3b56a9590688fe70bc'
OLD_RESULT_SHA = '4e0e677aa3b3c65728e2351017f299c2c8f8cf41aff69c7cdbabe93c6b68b30a'
MANIFESTS = {
    'manifest-rustc-aarch64-apple-darwin': '63877f7423dab866120519887a56dc4a6780e6ac9928fd6ea3ce8c02281a9658',
    'manifest-rust-std-aarch64-apple-darwin': 'dc34ab873acc111785b0d677e1dbbbf66cb387ee28e6d8325863f423b13c61b9',
}
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
START = time.monotonic()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(info):
    return {name: getattr(info, 'st_'+name) for name in FIELDS}


def guard(entry=False):
    require(time.monotonic()-START < 2400, 'overall observer deadline expired')
    free = shutil.disk_usage(ROOT).free
    require(free >= (24 if entry else 9)*2**30, 'compiler free-space gate refused')
    return free


def file_record(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'ordinary exact file route required')
    before = stamp(path.lstat())
    require(stat.S_ISREG(before['mode']) and before['size'] <= 512*2**20, 'bounded ordinary input/output file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256(); size = 0
    with os.fdopen(fd, 'rb') as stream:
        require(stamp(os.fstat(stream.fileno())) == before, 'opened input differs')
        while chunk := stream.read(2**20):
            digest.update(chunk); size += len(chunk)
            require(size <= 512*2**20, 'file exceeded read bound')
            guard()
        require(stamp(os.fstat(stream.fileno())) == before, 'input changed during read')
    require(stamp(path.lstat()) == before and size == before['size'], 'input replaced during read')
    return dict(sha256=digest.hexdigest(), bytes=size, identity=before)


def read(path, expected=None):
    row = file_record(path)
    require(row['bytes'] <= 2**20 and (expected is None or row['sha256'] == expected), 'bounded exact JSON input')
    value = json.loads(Path(path).read_bytes())
    require(file_record(path) == row, 'JSON changed during decoding')
    return value


def write(name, value, replace=False):
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    require(len(data) <= 2**20, 'bounded result record')
    path = OUT/name; temporary = path.with_name(path.name+'.tmp') if replace else path
    with temporary.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    if replace:
        os.replace(temporary, path)
    require(path.read_bytes() == data, 'record readback differs')


def work_size():
    total = 0; count = 0
    for root, directories, files in os.walk(WORK, followlinks=False):
        for name in directories + files:
            p = Path(root)/name; info = p.lstat(); count += 1
            require(count <= 512 and not stat.S_ISLNK(info.st_mode), 'unexpected owned output membership')
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
            else:
                require(stat.S_ISDIR(info.st_mode), 'unexpected owned output kind')
    require(total <= 128*2**20, 'fresh work exceeds 128MiB')
    return total


def limits(cpu):
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64*2**20, 64*2**20))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(index, spec, lock, records):
    label = f'{index:02d}-{spec["arm"]}-{spec.get("case", "dylib")}'
    record = dict(status='starting', command=spec['argv'], cwd=spec['cwd'], environment=spec['environment'],
        parent_pid=os.getpid(), parent_parent_pid=os.getppid(), started_at=time.time(),
        expected_returncode=spec['expected_returncode'], cpu_seconds=spec['child_cpu_seconds'],
        observer_seconds=spec['child_observer_seconds'], file_bytes=64*2**20,
        observation_errors=[], may_be_live=False, samples=[])
    records.append(record)
    def save():
        write(label+'-record.json', record, replace=(OUT/(label+'-record.json')).exists())
    def note(stage, error):
        record['observation_error_count'] = record.get('observation_error_count', 0)+1
        if len(record['observation_errors']) < 64:
            record['observation_errors'].append(dict(stage=stage, error=repr(error)))
    def observe_save():
        try:
            save()
        except BaseException as error:
            note('record-publication', error)
    guard(entry=True); work_size(); save()
    with (OUT/(label+'.stdout')).open('xb') as stdout, (OUT/(label+'.stderr')).open('xb') as stderr:
        child = subprocess.Popen(spec['argv'], cwd=spec['cwd'], env=spec['environment'], stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, preexec_fn=lambda: limits(spec['child_cpu_seconds']), pass_fds=(lock.fileno(),))
        deadline = min(time.monotonic()+spec['child_observer_seconds'], START+2400)
        record.update(pid=child.pid, spawned_at=time.time(), status='running', may_be_live=True)
        try:
            observe_save()
            while time.monotonic() < deadline:
                try:
                    child.wait(timeout=min(1, max(0.001, deadline-time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    try:
                        record['samples'].append(dict(time=time.time(), free_bytes=guard(), work_bytes=work_size()))
                    except BaseException as error:
                        note('resource-observation', error)
                    observe_save()
                except BaseException as error:
                    note('wait-observation', error)
                    time.sleep(min(.1, max(0, deadline-time.monotonic())))
        finally:
            # Record actual closure before potentially failing output reads.
            record.update(returncode=child.returncode, observation_finished_at=time.time())
            record.update(status='closed' if child.returncode is not None else 'unclosed-not-signalled',
                          may_be_live=child.returncode is None)
            if child.returncode is not None:
                record['finished_at'] = time.time()
            for stream in ['stdout', 'stderr']:
                try:
                    row = file_record(OUT/(label+'.'+stream)); record[stream] = row
                    require(row['bytes'] <= 2**20, 'compiler raw stream exceeds 1MiB')
                except BaseException as error:
                    note(stream+'-readback', error)
            observe_save()
    require(child.returncode is not None, 'child may remain live; no retry, signal or further compiler call')
    require(not record['observation_errors'], 'observation/publication failed after bounded wait')
    require(child.returncode == spec['expected_returncode'], 'unexpected compiler exit')
    require(record['stdout']['bytes'] == 0, 'unexpected compiler stdout')
    guard(); work_size()
    return label, record


def diagnostics(label, spec, cases):
    raw = (OUT/(label+'.stderr')).read_text()
    values = [json.loads(line) for line in raw.splitlines()]
    errors = []; normalized = []; aborts = []
    for value in values:
        require(value.get('$message_type') == 'diagnostic', 'unexpected compiler JSON message')
        level = value['level']
        require(level != 'warning', 'unexpected compiler warning')
        if level == 'error':
            if not value['spans']:
                match = re.fullmatch(r'aborting due to ([1-9][0-9]*) previous errors?', value['message'])
                require(match is not None,
                        'unexpected spanless compiler error')
                aborts.append(int(match.group(1)))
                continue
            errors.append(value)
        else:
            require(level == 'failure-note', 'unexpected standalone compiler diagnostic level')
    expected = [] if spec['role'] == 'build-macro-dylib' else cases[spec['case']]['errors']
    require(len(errors) == len(expected), 'unexpected number of primary errors')
    require(aborts == ([] if spec['expected_returncode'] == 0 else [len(errors)]),
            'exact abort summary must agree with retained primary errors')
    for error in errors:
        primary = [span for span in error['spans'] if span['is_primary']]
        code = error['code']['code'] if error['code'] is not None else None
        matches = [item for item in expected if item['code'] == code and item['message'] == error['message']
            and any(span['file_name'] == cases[spec['case']]['source'] and span['line_start'] == item['primary_line']
                    for span in primary)
            and ('help' not in item or any(child['level'] == 'help' and child['message'] == item['help']
                                          for child in error['children']))]
        require(len(matches) == 1, 'exact expected diagnostic message/code/help/source span differs')
        expected = [item for item in expected if item is not matches[0]]
        normalized.append(dict(level=error['level'], code=code, message=error['message'],
            primary_spans=[{k: span[k] for k in ['file_name','line_start','line_end','column_start','column_end']}
                           for span in primary],
            children=[dict(level=child['level'], message=child['message']) for child in error['children']]))
    require(not expected and (spec['expected_returncode'] != 0 or not values), 'unexpected successful compiler diagnostics')
    return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))


def dependency_proof(spec):
    output = Path(spec['output'])
    if spec['expected_returncode'] != 0:
        require(not os.path.lexists(output), 'failed compiler emitted success metadata')
        return dict(success_output_absent=True)
    row = file_record(output); dep = Path(spec['depinfo']); dep_row = file_record(dep)
    require(dep_row['bytes'] <= 2**20, 'bounded dependency proof')
    text = dep.read_text()
    if spec['role'] == 'caller':
        required = str(WORK/spec['arm']/'libarena04_macros.dylib')
        forbidden = str(WORK/('stock' if spec['arm'] == 'candidate' else 'candidate')/'libarena04_macros.dylib')
        require(required in text and forbidden not in text, 'caller selected the wrong macro dylib')
    elif spec['arm'] == 'candidate':
        require(str(BRIDGE/'libproc_macro.rlib') in text and str(BRIDGE/'librustc_literal_escaper.rlib') in text
            and '/libproc_macro-9dac517e5d77c501.' not in text, 'candidate client linkage differs')
    else:
        require('/libproc_macro-9dac517e5d77c501.' in text and str(BRIDGE/'libproc_macro.rlib') not in text,
                'stock client linkage differs')
    return dict(output=row, depinfo=dict(path=str(dep), **dep_row))


def input_paths(plan):
    old = read(OLD/'source.json', OLD_SOURCE_SHA); result = read(OLD/'result.json', OLD_RESULT_SHA)
    require(result['status'] == 'passed' and result['tests_passed'] == 8
            and result['library_sha256'] == plan['candidate_library']['saved_sha256'], 'actual prior library qualification differs')
    expected = dict(old['source_pins']); expected[str(BRIDGE/'libproc_macro.rlib')] = result['library_sha256']
    expected[str(BRIDGE/'librustc_literal_escaper.rlib')] = 'c7604580e6e8c28123dd4fe1a14a7ef222495f8efa42f09539f7cac6b0ccbf81'
    expected.update({name: row['sha256'] for name, row in plan['source_files'].items()})
    expected.update({str(SOURCE/'plan.json'): PLAN_SHA, str(OLD/'source.json'): OLD_SOURCE_SHA,
                     str(OLD/'result.json'): OLD_RESULT_SHA})
    paths = set(map(Path, expected)) | {Path(__file__), SOURCE/'README.md', SOURCE/'source-review.json'}
    for name, digest in MANIFESTS.items():
        path = TC/'lib/rustlib'/name; expected[str(path)] = digest; paths.add(path)
        require(file_record(path)['sha256'] == digest, 'installed component manifest changed')
        declared = path.read_text().splitlines()
        require(len(declared) <= 128 and all(line.startswith('file:') for line in declared), 'bounded component manifest required')
        selected = declared if name.startswith('manifest-rust-std-') else [line for line in declared if line in {
            'file:bin/rustc', 'file:lib/libLLVM.dylib', 'file:lib/librustc_driver-74f15b932c10ca27.dylib'}]
        for line in selected:
            relative = Path(line[5:]); require(not relative.is_absolute() and '..' not in relative.parts, 'component route escape')
            paths.add(TC/relative)
    require(len(paths) <= 128, 'bounded exact compiler/library/source selection')
    rows = {str(path): file_record(path) for path in sorted(paths)}
    for name, digest in expected.items():
        require(rows[name]['sha256'] == digest, 'qualified source or selected library changed')
    return rows


def main():
    require(Path(__file__) == SOURCE/'run_once.py' and Path.cwd() == ROOT, 'exact runner path and cwd')
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh work/results required')
    plan = read(SOURCE/'plan.json', PLAN_SHA)
    require(len(plan['commands']) == 20 and len(plan['cases']) == 9 and plan['actual_result'] is None, 'exact unrun fixed fixture plan')
    require(plan['compiler'] == str(TC/'bin/rustc') and plan['sysroot'] == str(TC), 'matching installed compiler only')
    guard(entry=True); OUT.mkdir(); WORK.mkdir()
    for arm in ['stock', 'candidate']:
        (WORK/arm).mkdir(); (WORK/arm/'tmp').mkdir()
    shutil.copyfile(SOURCE/'run_once.py', OUT/'run_once.py')
    shutil.copyfile(SOURCE/'plan.json', OUT/'plan.json')
    records = []; summary = dict(status='waiting', started_at=time.time(), parent_pid=os.getpid(),
        plan_sha256=PLAN_SHA, command_records=records, compiler_children=0, signals=[], retries=0,
        real_proc_macro_client_integration=False, compiler_distribution_qualified=False, benchmark=False)
    write('execution.json', summary)
    lock = None
    try:
        require(LOCK.resolve(strict=True) == LOCK and stat.S_ISREG(LOCK.lstat().st_mode), 'ordinary canonical lock')
        lock = LOCK.open('r+'); named = LOCK.stat(); held = os.fstat(lock.fileno())
        require((named.st_dev,named.st_ino,named.st_nlink) == (held.st_dev,held.st_ino,1), 'canonical identity differs')
        deadline = time.monotonic()+600
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'canonical wait expired')
                time.sleep(.25)
        summary.update(status='admitted', admitted_at=time.time(), free_bytes_before=guard(entry=True))
        before = input_paths(plan); write('inputs-before.json', before)
        cases = {case['name']: case for case in plan['cases']}; compared = {}; proofs = []; built = {}
        for index, spec in enumerate(plan['commands']):
            dylib = str(WORK/spec['arm']/'libarena04_macros.dylib')
            if spec['role'] == 'caller':
                require(file_record(dylib) == built[dylib], 'macro dylib changed before caller')
            label, record = run(index, spec, lock, records)
            summary['compiler_children'] += 1
            observed = diagnostics(label, spec, cases); dep = dependency_proof(spec)
            if spec['role'] == 'caller':
                require(file_record(dylib) == built[dylib], 'macro dylib changed during caller')
                key = spec['case']
                if spec['arm'] == 'stock':
                    compared[key] = observed
                else:
                    require(observed == compared[key], 'stock/candidate stable diagnostic fields differ')
            else:
                built[dylib] = dep['output']
            proofs.append(dict(label=label, diagnostics=observed, dependency=dep))
            write(label+'-verification.json', proofs[-1]); write('execution.json', summary, replace=True)
        after = {name: file_record(name) for name in before}; write('inputs-after.json', after)
        require(after == before, 'selected compiler/library/source inputs changed')
        require(all(file_record(name) == row for name, row in built.items()), 'final macro dylib changed')
        write('macro-dylibs.json', built)
        require(len(records) == 20 and all(row['status'] == 'closed' and not row['may_be_live'] for row in records), 'all actual children must close')
        summary.update(status='passed', real_proc_macro_client_integration=True, finished_at=time.time(),
            free_bytes_after=guard(), work_bytes=work_size(), compared_cases=9, input_files=len(before))
    except BaseException as error:
        summary.update(status='failed', error=repr(error), observed_at=time.time())
        raise
    finally:
        if lock is not None:
            lock.close()
            summary['parent_lock_closed_at'] = time.time()
            if all(not row['may_be_live'] for row in records) and 'admitted_at' in summary:
                summary['canonical_released_at'] = time.time()
        summary['compiler_children'] = sum('pid' in row for row in records)
        try:
            write('execution.json', summary, replace=True)
        except BaseException as error:
            print(json.dumps(dict(status='final-publication-failed', error=repr(error), observed=summary)), flush=True)
            raise
    write('result.json', dict(status='passed', compiler_children=20, caller_cases_per_arm=9,
        execution_sha256=file_record(OUT/'execution.json')['sha256'], inputs_unchanged=True,
        real_proc_macro_client_integration=True, installed_compiler_server_unchanged=True,
        compiler_distribution_qualified=False, benchmark=False))
    print(json.dumps(dict(status='passed', result_sha256=file_record(OUT/'result.json')['sha256'])))


if __name__ == '__main__':
    main()

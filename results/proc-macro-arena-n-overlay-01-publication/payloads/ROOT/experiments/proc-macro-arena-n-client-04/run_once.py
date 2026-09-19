"""One-shot matched N client builds and real compiler tests. No retries or signals."""
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
SOURCE = ROOT/'experiments/proc-macro-arena-n-client-04'
WORK = ROOT/'.work/proc-macro-arena-n-client-04'
OUT = ROOT/'results/proc-macro-arena-n-client-04'
TC = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin/stage1')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PLAN_SHA = 'e7cf786c2ac4ec52890a856edb38ea8d3221a129781f2f3eead8955a57f189e1'
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
    require(free >= (14 if entry else 9)*2**30, 'compiler free-space gate refused')
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
    require(row['bytes'] <= 4*2**20 and (expected is None or row['sha256'] == expected), 'bounded exact JSON input')
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
    for root, directories, files in owned_walk():
        for name in directories + files:
            p = Path(root)/name; info = p.lstat(); count += 1
            require(count <= 1024 and not stat.S_ISLNK(info.st_mode), 'unexpected owned output membership')
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
            else:
                require(stat.S_ISDIR(info.st_mode), 'unexpected owned output kind')
    require(total <= 256*2**20, 'fresh work/results exceed 256MiB')
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
    require(spec['role'] == 'run-whole-crate-tests' or record['stdout']['bytes'] == 0, 'unexpected compiler stdout')
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
    expected = cases[spec['case']]['errors'] if spec['role'] == 'caller' else []
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


def owned_walk():
    for base in [WORK, OUT]:
        yield from os.walk(base, followlinks=False)


def expected_identity(values):
    require(type(values) is list and len(values) == 7 and all(type(v) is int for v in values), 'exact saved identity')
    dev, ino, mode, size, mtime, ctime, links = values
    return dict(dev=dev, ino=ino, mode=mode, size=size, mtime_ns=mtime, ctime_ns=ctime, nlink=links)


def runtime_readback(inventory, payloads):
    require(inventory['root'] == str(TC) and inventory['file_count'] == 63 and inventory['link_count'] == 2,
            'complete unchanged N runtime required')
    expected = inventory['entries']; observed = {}; directories = {}
    for root, dirs, files in os.walk(TC, followlinks=False):
        directory = Path(root)
        require(directory.resolve(strict=True) == directory and stat.S_ISDIR(directory.lstat().st_mode), 'ordinary runtime directory')
        directories[str(directory.relative_to(TC))] = stamp(directory.lstat())
        require(len(directories) <= 32, 'bounded runtime directories')
        for name in dirs + files:
            path = directory/name; relative = str(path.relative_to(TC)); info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                continue
            require(relative in expected, 'extra runtime member')
            row = expected[relative]; identity = stamp(info)
            require(identity == expected_identity(row['stamp']), 'saved N runtime identity changed')
            if row['kind'] == 'link':
                require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == row['target']
                        and str(path.resolve(strict=True)) == row['resolved'], 'exact declared source link changed')
                observed[relative] = dict(kind='link', identity=identity, target=row['target'], resolved=row['resolved'])
            else:
                require(row['kind'] == 'file' and stat.S_ISREG(info.st_mode), 'ordinary runtime file')
                actual = file_record(path) if payloads else dict(identity=identity, sha256=row['sha256'], bytes=identity['size'])
                require(actual['sha256'] == row['sha256'] and actual['identity'] == identity, 'N runtime payload changed')
                observed[relative] = dict(kind='file', **actual)
            require(stamp(path.lstat()) == identity, 'runtime entry changed during readback')
            require(len(observed) <= 65, 'bounded runtime membership')
    require(set(observed) == set(expected) and len(observed) == 65, 'complete runtime membership differs')
    require(directories == inventory['directories'], 'complete runtime directory identity/membership differs')
    require(sum(r['bytes'] for r in observed.values() if r['kind'] == 'file') == inventory['logical_file_bytes'], 'runtime byte accounting differs')
    return dict(entries=observed, directories=directories, full_payload_readback=payloads)


def input_paths(plan):
    require(len(plan['inputs']) <= 128, 'bounded source and provenance inputs')
    rows = {}
    for name, expected in plan['inputs'].items():
        require(name == expected['path'], 'input route differs')
        actual = file_record(name)
        require(actual == {k:expected[k] for k in ['sha256','bytes','identity']}, 'exact source or provenance input changed')
        rows[name] = actual
    for path in [SOURCE/'plan.json', SOURCE/'run_once.py', SOURCE/'README.md', SOURCE/'source-review.json']:
        rows[str(path)] = file_record(path)
    require(rows[str(SOURCE/'plan.json')]['sha256'] == PLAN_SHA, 'plan changed')
    bindings = read(SOURCE/'source-bindings.json',plan['source_bindings']['sha256'])
    for pair in bindings['copies'].values():
        require(rows[pair['origin']['path']]['sha256'] == rows[pair['copy']['path']]['sha256'], 'copied source provenance differs')
    differences = []
    for name in sorted(bindings['copies']):
        path = Path(name)
        if path.is_relative_to(SOURCE/'source/stock/proc_macro'):
            rel = path.relative_to(SOURCE/'source/stock/proc_macro')
            other = str(SOURCE/'source/candidate/proc_macro'/rel)
            if rows[name]['sha256'] != rows[other]['sha256']:
                differences.append(str(rel))
    require(differences == bindings['source_difference_paths'], 'only Arena and Symbol may differ between client sources')
    return rows


def test_result(label, spec):
    require((OUT/(label+'.stderr')).read_bytes() == b'', 'test harness stderr must be empty')
    raw = (OUT/(label+'.stdout')).read_text(); lines = [line for line in raw.splitlines() if line]
    names = spec['tests']; count = len(names)
    require(len(lines) == count+2 and lines[0] == f'running {count} tests', 'exact native test count/header')
    require(lines[1:-1] == [f'test {name} ... ok' for name in names], 'all exact native tests must pass without skips')
    require(re.fullmatch(r'test result: ok\. '+str(count)+r' passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in [0-9]+\.[0-9]+s', lines[-1]) is not None,
            'exact native test result summary')
    return dict(tests=names, passed=count, stock_empty_harness_is_smoke_only=spec['arm']=='stock')


def dependency_proof(spec, built):
    outputs = [spec['output']] + ([spec['metadata']] if 'metadata' in spec else [])
    if spec['expected_returncode'] != 0:
        require(all(not os.path.lexists(p) for p in outputs), 'failed compiler emitted success metadata')
        return dict(success_outputs_absent=outputs)
    rows = {name:file_record(name) for name in outputs}
    dep = Path(spec['depinfo']); dep_row = file_record(dep)
    require(dep_row['bytes'] <= 2**20, 'bounded dependency proof')
    text = dep.read_text(); require(file_record(dep) == dep_row, 'dep-info changed during reading')
    # Binary dep-info must name actual source and matching split metadata/code pairs.
    require('/.rustup/toolchains/' not in text, 'installed T artifact entered matched N dependency closure')
    for arg in spec['argv']:
        if arg.endswith('.rs'):
            require(arg in text, 'actual Rust source missing from dep-info')
    if spec['role'] != 'caller':
        require('/libproc_macro-452900db9815e688.' not in text, 'old N client silently selected')
    literal_dependency = None
    if spec['role'] in ['build-stock-client','build-candidate-client','build-whole-crate-tests','build-macro-dylib']:
        metadata_only = spec['role'] in ['build-stock-client','build-candidate-client']
        direct_literal = spec['role'] != 'build-macro-dylib'
        supplied = {}
        for suffix in ['rlib','rmeta']:
            name = str(WORK/'dependency'/('librustc_literal_escaper-arena04_n_dep01.'+suffix))
            require(file_record(name) == built[name], 'matched normal literal artifact changed')
            if direct_literal:
                require(any(spec['argv'][i:i+2] == ['--extern','rustc_literal_escaper='+name]
                            for i in range(len(spec['argv'])-1)), 'explicit literal metadata/code argument missing')
            if suffix == 'rmeta' or not metadata_only:
                require(name in text, 'required literal crate source missing from dep-info')
            supplied[suffix] = dict(path=name, **built[name])
        # locator.rs::extract_one intentionally does not discover the unused
        # rlib when producing an rlib after loading its rmeta. Record the
        # supplied code archive without mislabeling it as selected or linked.
        literal_dependency = dict(metadata_only_rlib_build=metadata_only, supplied=supplied,
            direct_extern_required=direct_literal,
            dependency_route='direct' if direct_literal else 'transitive-through-matched-proc-macro',
            required_depinfo_flavors=['rmeta'] if metadata_only else ['rlib','rmeta'],
            code_archive_linkage_required=not metadata_only,
            code_archive_present_in_depinfo=supplied['rlib']['path'] in text)
        require('/librustc_literal_escaper-f4f532eb55f87a02.' not in text, 'old private literal selected')
    if spec['role'] == 'build-macro-dylib':
        for suffix in ['rlib','rmeta']:
            name = str(WORK/spec['arm']/(f'libproc_macro-arena04_n_{spec["arm"]}01.'+suffix))
            require(name in text and file_record(name) == built[name], 'matched N client pair not linked')
        other = 'stock' if spec['arm']=='candidate' else 'candidate'
        require(str(WORK/other) not in text, 'other arm entered macro build')
    if spec['role'] == 'caller':
        name = str(WORK/'macro-tests'/spec['arm']/'libarena04_macros.dylib')
        other = str(WORK/'macro-tests'/('stock' if spec['arm']=='candidate' else 'candidate')/'libarena04_macros.dylib')
        require(name in text and other not in text and file_record(name) == built[name], 'caller selected wrong macro dylib')
    proof = dict(outputs=rows,depinfo=dict(path=str(dep),**dep_row))
    if literal_dependency is not None:
        proof['normal_literal_dependency'] = literal_dependency
    return proof


def main():
    require(Path(__file__) == SOURCE/'run_once.py' and Path.cwd() == ROOT, 'exact runner path and cwd')
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh work/results required')
    plan = read(SOURCE/'plan.json',PLAN_SHA)
    require(len(plan['commands']) == 27 and len(plan['cases']) == 9 and plan['actual_result'] is None, 'fixed unrun plan')
    require(plan['compiler'] == str(TC/'bin/rustc') and plan['sysroot'] == str(TC), 'matched N compiler only')
    guard(entry=True); OUT.mkdir(); WORK.mkdir()
    for relative in ['dependency','stock','candidate','macro-tests/stock','macro-tests/candidate']:
        (WORK/relative/'tmp').mkdir(parents=True)
    shutil.copyfile(SOURCE/'run_once.py',OUT/'run_once.py'); shutil.copyfile(SOURCE/'plan.json',OUT/'plan.json')
    records=[]; summary=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),plan_sha256=PLAN_SHA,
        command_records=records,children=0,signals=[],retries=0,real_N_external_client_integration=False,
        compiler_distribution_qualified=False,runtime_composition_qualified=False,benchmark=False)
    write('execution.json',summary);lock=None
    try:
        require(LOCK.resolve(strict=True)==LOCK and stat.S_ISREG(LOCK.lstat().st_mode),'ordinary canonical lock')
        lock=LOCK.open('r+'); named=LOCK.stat();held=os.fstat(lock.fileno())
        require((named.st_dev,named.st_ino,named.st_nlink)==(held.st_dev,held.st_ino,1),'canonical identity differs')
        deadline=time.monotonic()+600
        while True:
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                require(time.monotonic()<deadline,'canonical wait expired');time.sleep(.25)
        summary.update(status='admitted',admitted_at=time.time(),free_bytes_before=guard(entry=True))
        before=input_paths(plan);write('inputs-before.json',before)
        inventory=read(SOURCE/'runtime-inventory.json',plan['runtime_inventory']['sha256'])
        compiled=read(inventory['compiled']['path'],inventory['compiled']['sha256'])
        require(compiled['stage1']==inventory['entries'] and compiled['source_identity']==inventory['source_identity'], 'old N compiler proof differs')
        runtime_before=runtime_readback(inventory,True);write('runtime-before.json',runtime_before)
        cases={case['name']:case for case in plan['cases']};compared={};proofs=[];built={}
        for index,spec in enumerate(plan['commands']):
            current=runtime_readback(inventory,False)
            require(current['entries']==runtime_before['entries'] and current['directories']==runtime_before['directories'], 'N runtime identity/membership changed')
            require(all(file_record(name)==row for name,row in built.items()),'previously built artifact changed')
            label,record=run(index,spec,lock,records)
            summary['children']+=1
            if spec['role']=='run-whole-crate-tests':
                proof=dict(label=label,native_tests=test_result(label,spec))
            else:
                observed=diagnostics(label,spec,cases);dep=dependency_proof(spec,built)
                if spec['role']=='caller':
                    key=spec['case']
                    if spec['arm']=='stock':compared[key]=observed
                    else:require(observed==compared[key],'stock/candidate stable diagnostics differ')
                if spec['expected_returncode']==0:built.update(dep['outputs'])
                proof=dict(label=label,diagnostics=observed,dependency=dep)
            require(all(file_record(name)==row for name,row in built.items()),'built artifact changed during child')
            proofs.append(proof);write(label+'-verification.json',proof);write('execution.json',summary,replace=True)
        after={name:file_record(name) for name in before};write('inputs-after.json',after)
        require(after==before,'source/provenance input changed')
        runtime_after=runtime_readback(inventory,True);write('runtime-after.json',runtime_after)
        require(runtime_after==runtime_before,'full N runtime changed')
        write('built-artifacts.json',built)
        require(len(records)==27 and all(row['status']=='closed' and not row['may_be_live'] for row in records),'all children must close')
        summary.update(status='passed',real_N_external_client_integration=True,finished_at=time.time(),
            free_bytes_after=guard(),work_and_results_bytes=work_size(),compared_cases=9,input_files=len(before),
            runtime_files=63,runtime_links=2,native_tests=plan['whole_crate_test_names'])
    except BaseException as error:
        summary.update(status='failed',error=repr(error),observed_at=time.time());raise
    finally:
        if lock is not None:
            lock.close();summary['parent_lock_closed_at']=time.time()
            if all(not row['may_be_live'] for row in records) and 'admitted_at' in summary:
                summary['canonical_released_at']=time.time()
        summary['children']=sum('pid' in row for row in records)
        try:write('execution.json',summary,replace=True)
        except BaseException as error:
            print(json.dumps(dict(status='final-publication-failed',error=repr(error),observed=summary)),flush=True);raise
    write('result.json',dict(status='passed',children=27,library_builds=3,whole_crate_test_builds=2,
        native_tests_passed={'stock':0,'candidate':13},stock_empty_harness_is_smoke_only=True,caller_cases_per_arm=9,
        execution_sha256=file_record(OUT/'execution.json')['sha256'],inputs_unchanged=True,complete_N_runtime_unchanged=True,
        real_N_external_client_integration=True,compiler_server_unchanged=True,builtin_quote_optimized=False,
        compiler_distribution_qualified=False,runtime_composition_qualified=False,holdout_qualified=False,benchmark=False))
    print(json.dumps(dict(status='passed',result_sha256=file_record(OUT/'result.json')['sha256'])))


if __name__ == '__main__':
    main()


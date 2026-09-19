"""One-shot default proc_macro discovery through finite matched N overlays."""
from pathlib import Path
import argparse
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
SOURCE = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/proc-macro-arena-n-overlay-01')
WORK = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/proc-macro-arena-n-overlay-01')
OUT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/proc-macro-arena-n-overlay-01')
TC = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source/build/aarch64-apple-darwin/stage1')
LOCK = Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PLAN_SHA = '2a47bdd12f42c197438b11a9114e76551ed037875b2e39d773c987c9606b2356'
FIELDS = ("dev", "ino", "mode", "nlink", "size", "mtime_ns", "ctime_ns")
START = time.monotonic()
ALIASES = {}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(info):
    return {name: getattr(info, 'st_'+name) for name in FIELDS}


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

def guard(entry=False):
    require(time.monotonic()-START < 2400, 'overall observer deadline expired')
    free = shutil.disk_usage(ROOT).free
    require(free >= (16 if entry else 9)*2**30, 'compiler free-space gate refused')
    return free


def work_size():
    total = 0; count = 0
    for root, directories, files in owned_walk():
        for name in directories + files:
            p = Path(root)/name; info = p.lstat(); count += 1
            require(count <= 1024, 'bounded owned output membership')
            if stat.S_ISLNK(info.st_mode):
                require(str(p) in ALIASES and os.readlink(p) == ALIASES[str(p)], 'only finite declared overlay links')
                require(p.resolve(strict=True) == Path(ALIASES[str(p)]), 'overlay link resolved elsewhere')
                total += info.st_size
            elif stat.S_ISREG(info.st_mode):
                total += info.st_size
            else:
                require(stat.S_ISDIR(info.st_mode), 'unexpected owned output kind')
    require(total <= 256*2**20, 'fresh work/results exceed 256MiB')
    return total


def source_readback(plan):
    require(len(plan['inputs']) <= 40, 'bounded fixture and provenance inputs')
    rows = {}
    for name, expected in plan['inputs'].items():
        require(name == expected['path'], 'input route differs')
        actual = file_record(name)
        require(actual == {k:expected[k] for k in ['sha256','bytes','identity']}, 'exact source or provenance input changed')
        rows[name] = actual
    for name in ['plan.json','run_once.py','README.md','source-review.json','prerequisite-template.json']:
        rows[str(SOURCE/name)] = file_record(SOURCE/name)
    require(rows[str(SOURCE/'plan.json')]['sha256'] == PLAN_SHA, 'plan changed')
    bindings = read(SOURCE/'source-bindings.json', plan['source_bindings']['sha256'])
    require(len(bindings['copies']) == 9, 'exact nine original fixture files')
    for copy, pair in bindings['copies'].items():
        require(copy == pair['copy']['path'] and rows[copy]['sha256'] == rows[pair['origin']['path']]['sha256'], 'fixture bytes differ')
    return rows


def prerequisite(plan, expected_sha):
    require(re.fullmatch('[0-9a-f]{64}', expected_sha) is not None, 'actual prerequisite SHA is mandatory')
    path = Path(plan['prerequisite']['path']); first = file_record(path)
    binding = read(path, expected_sha)
    require(binding['policy'] == 'reviewed-passed-n-client04-for-default-discovery-v1'
            and binding['actual_success'] is True, 'successful reviewed N04 prerequisite required')
    owner = Path(plan['prerequisite']['owner_source']); output = Path(plan['prerequisite']['owner_results'])
    wanted = {name:str(output/name) for name in ['result.json','execution.json','built-artifacts.json','inputs-before.json','inputs-after.json','runtime-before.json','runtime-after.json']}
    wanted.update({'owner-plan':str(owner/'plan.json'),'owner-runner':str(owner/'run_once.py'),
                   'independent-readback':plan['prerequisite']['independent_readback']['path']})
    require(set(binding['proofs']) == set(wanted), 'exact completed owner proof set')
    require(binding['proofs']['owner-plan']['sha256'] == plan['inputs'][str(owner/'plan.json')]['sha256']
            and binding['proofs']['owner-runner']['sha256'] == plan['inputs'][str(owner/'run_once.py')]['sha256'],
            'exact reviewed successful-owner source required')
    proofs = {}; rows = {str(path):first}
    for name, target in wanted.items():
        ref = binding['proofs'][name]
        require(set(ref) == {'path','sha256'} and ref['path'] == target
                and isinstance(ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'actual proof route/hash required')
        record = file_record(target); require(record['sha256'] == ref['sha256'], 'completed owner proof changed')
        rows[target] = record
        if name != 'owner-runner':
            proofs[name] = read(target, ref['sha256'])
    result = proofs['result.json']; execution = proofs['execution.json']; owner_plan = proofs['owner-plan']
    audit = proofs['independent-readback']
    require(binding['proofs']['independent-readback'] == plan['prerequisite']['independent_readback']
            and audit['status'] == 'verified' and audit['command_count'] == len(audit['children']) == 27
            and audit['stable_caller_pairs'] == 9 and audit['current_inputs_match'] is True
            and audit['full_input_before_after_rows'] == 122
            and audit['native_tests']['candidate']['passed'] == 13
            and audit['native_tests']['stock']['passed'] == 0
            and audit['native_tests']['stock']['stock_empty_harness_is_smoke_only'] is True
            and audit['no_target_imports_or_child_calls'] is True
            and audit['real_N_external_client_integration'] is True
            and audit['benchmark'] is audit['compiler_distribution_qualified']
            is audit['runtime_composition_qualified'] is audit['holdout_qualified'] is False,
            'independently verified N04 scope')
    for name, key in [('result','result.json'),('execution','execution.json'),('plan','owner-plan'),('runner','owner-runner')]:
        require(audit[name] == binding['proofs'][key], 'independent owner/source reference differs')
    require(audit['runtime']['before'] == binding['proofs']['runtime-before.json']
            and audit['runtime']['after'] == binding['proofs']['runtime-after.json']
            and audit['runtime']['full_payload_rehash'] is audit['runtime']['complete_membership'] is True
            and audit['runtime']['files'] == 63 and audit['runtime']['links'] == 2
            and audit['runtime']['logical_file_bytes'] == 564106543, 'independent full runtime proof')
    require(result['status'] == 'passed' and result['children'] == 27
            and result['library_builds'] == 3 and result['whole_crate_test_builds'] == 2
            and result['native_tests_passed'] == {'stock':0,'candidate':13}
            and result['caller_cases_per_arm'] == 9 and result['inputs_unchanged'] is True
            and result['complete_N_runtime_unchanged'] is True
            and result['real_N_external_client_integration'] is True
            and result['compiler_server_unchanged'] is True
            and result['builtin_quote_optimized'] is result['compiler_distribution_qualified']
            is result['runtime_composition_qualified'] is result['holdout_qualified'] is result['benchmark'] is False,
            'complete successful N04 scope required')
    require(result['execution_sha256'] == binding['proofs']['execution.json']['sha256']
            and execution['status'] == 'passed' and execution['children'] == 27
            and execution['plan_sha256'] == binding['proofs']['owner-plan']['sha256']
            and execution['started_at'] <= execution['admitted_at'] <= execution['finished_at']
            <= execution['parent_lock_closed_at'] <= execution['canonical_released_at']
            and execution['signals'] == [] and execution['retries'] == 0,
            'actual N04 owner and canonical closure')
    require(owner_plan['compiler'] == str(TC/'bin/rustc') and owner_plan['sysroot'] == str(TC)
            and len(owner_plan['commands']) == len(execution['command_records']) == 27,
            'exact matched N04 command plan')
    for record, spec in zip(execution['command_records'], owner_plan['commands']):
        require(record['status'] == 'closed' and record['may_be_live'] is False
                and record['returncode'] == record['expected_returncode'] == spec['expected_returncode']
                and record['command'] == spec['argv'] and record['cwd'] == spec['cwd']
                and record['environment'] == spec['environment'] and not record['observation_errors']
                and execution['admitted_at'] <= record['started_at'] <= record['spawned_at']
                <= record['finished_at'] <= execution['finished_at'], 'all actual N04 children closed correctly')
    before = proofs['inputs-before.json']; after = proofs['inputs-after.json']
    require(before == after and len(before) <= 160, 'full N04 source before/after')
    for name, saved in before.items():
        require(file_record(name) == saved, 'completed N04 source/provenance changed')
        rows[name] = saved
    require(before[str(owner/'plan.json')]['sha256'] == binding['proofs']['owner-plan']['sha256']
            and before[str(owner/'run_once.py')]['sha256'] == binding['proofs']['owner-runner']['sha256'],
            'actual source associations required')
    runtime = proofs['runtime-before.json']
    require(runtime == proofs['runtime-after.json'] and runtime['full_payload_readback'] is True
            and len(runtime['entries']) == 65, 'complete actual N runtime association')
    selected = binding['selected_artifacts']; wanted_artifacts = set()
    for names in plan['overlay']['owned_per_arm'].values():
        wanted_artifacts.update(names)
    require(set(selected) == wanted_artifacts and len(selected) == 6, 'exact six prerequisite artifacts')
    for name, saved in selected.items():
        require(type(saved) is dict and saved == proofs['built-artifacts.json'][name] == audit['built_artifacts'][name]
                and file_record(name) == saved, 'actual N04 artifact hash and identity required')
        rows[name] = saved
    require(file_record(path) == first, 'prerequisite changed during authentication')
    return binding, rows, runtime


def copy_ordinary(source, dest, expected):
    require(file_record(source) == expected, 'source artifact changed before copy')
    digest = hashlib.sha256(); count = 0
    with Path(source).open('rb') as stream, dest.open('xb') as output:
        while chunk := stream.read(2**20):
            output.write(chunk); digest.update(chunk); count += len(chunk); guard()
        output.flush(); os.fsync(output.fileno())
    actual = file_record(dest)
    require(digest.hexdigest() == actual['sha256'] == expected['sha256']
            and count == actual['bytes'] == expected['bytes'] and file_record(source) == expected,
            'exact artifact copy with full readback')
    return actual


def create_overlays(plan, selected):
    overlay = plan['overlay']; expected_links = overlay['aliases']; owned = {}
    require(len(expected_links) == 52 and len(overlay['excluded_original_paths']) == 4, 'finite overlay scope')
    for arm in ['stock','candidate']:
        root = WORK/arm/'sysroot'
        for relative in overlay['directories']:
            (root/relative).mkdir(parents=True, exist_ok=True)
        for relative, declaration in expected_links.items():
            target = Path(declaration['path']); destination = root/relative
            require(target == TC/relative and declaration['record']['kind'] == 'file'
                    and target.resolve(strict=True) == target
                    and stamp(target.lstat()) == expected_identity(declaration['record']['stamp']),
                    'exact ordinary already-read N alias target')
            ALIASES[str(destination)] = str(target)
            os.symlink(str(target), destination)
        for source in overlay['owned_per_arm'][arm]:
            destination = root/'lib/rustlib/aarch64-apple-darwin/lib'/Path(source).name
            owned[str(destination)] = copy_ordinary(source, destination, selected[source])
        require(all(not os.path.lexists(root/path) for path in overlay['excluded_original_paths']), 'old client/literal cannot enter overlay')
    return owned


def overlay_readback(plan, owned):
    observed = {}; directories = {}
    for arm in ['stock','candidate']:
        base = WORK/arm/'sysroot'; found = set(); found_dirs = set()
        expected_names = {str(base/relative) for relative in plan['overlay']['aliases']}
        expected_names.update(name for name in owned if Path(name).is_relative_to(base))
        for root, dirs, files in os.walk(base, followlinks=False):
            path = Path(root); relative = str(path.relative_to(base)); found_dirs.add(relative)
            require(relative in plan['overlay']['directories'] and path.resolve(strict=True) == path, 'ordinary finite overlay directories')
            directories[str(path)] = stamp(path.lstat())
            for name in dirs + files:
                child = path/name; identity = stamp(child.lstat())
                if stat.S_ISDIR(identity['mode']):
                    continue
                key = str(child); found.add(key)
                require(key in expected_names, 'unexpected overlay member')
                if key in ALIASES:
                    target = ALIASES[key]
                    require(stat.S_ISLNK(identity['mode']) and os.readlink(child) == target
                            and child.resolve(strict=True) == Path(target), 'exact N link association')
                    relative = str(child.relative_to(base)); row = plan['overlay']['aliases'][relative]['record']
                    require(stamp(Path(target).lstat()) == expected_identity(row['stamp']), 'unchanged N alias target identity')
                    observed[key] = dict(kind='link',identity=identity,target=target,resolved=target)
                else:
                    require(file_record(child) == owned[key], 'owned client/literal copy changed')
                    observed[key] = dict(kind='file',**owned[key])
            require(len(found) <= 56 and len(found_dirs) <= 7, 'bounded overlay membership')
        require(found == expected_names and found_dirs == set(plan['overlay']['directories']), 'complete overlay membership')
    require(len(observed) == 112 and len(directories) == 14, 'two exact overlays')
    return dict(entries=observed,directories=directories,old_client_and_literal_absent=True)


def dependency_proof(spec, built, owned):
    outputs = [spec['output']]
    if spec['expected_returncode'] != 0:
        require(all(not os.path.lexists(p) for p in outputs), 'failed compiler emitted success metadata')
        return dict(success_outputs_absent=outputs)
    rows = {name:file_record(name) for name in outputs}
    dep = Path(spec['depinfo']); dep_row = file_record(dep)
    require(dep_row['bytes'] <= 2**20, 'bounded dependency proof')
    text = dep.read_text(); require(file_record(dep) == dep_row, 'dep-info changed during reading')
    require('/.rustup/toolchains/' not in text and 'libproc_macro-452900db9815e688.' not in text
            and 'librustc_literal_escaper-f4f532eb55f87a02.' not in text, 'old/T client or literal fallback')
    for arg in spec['argv']:
        if arg.endswith('.rs'):
            require(arg in text, 'actual Rust source missing from dep-info')
    arm = spec['arm']; other = 'stock' if arm == 'candidate' else 'candidate'
    require(str(WORK/other/'sysroot') not in text, 'opposite overlay selected')
    selected = {}
    if spec['role'] == 'build-macro-dylib':
        require(not any(arg.startswith(('proc_macro=','rustc_literal_escaper=','dependency=')) for arg in spec['argv']), 'default discovery cannot use explicit dependency override')
        for name,row in owned.items():
            if Path(name).is_relative_to(WORK/arm/'sysroot'):
                require(name in text and file_record(name) == row, 'default-discovered client and transitive literal pairs must be linked')
                selected[name] = row
        require(len(selected) == 4, 'exact matched owned default dependencies')
    if spec['role'] == 'caller':
        name = str(WORK/'macro-tests'/arm/'libarena04_macros.dylib')
        opposite = str(WORK/'macro-tests'/other/'libarena04_macros.dylib')
        require(name in text and opposite not in text and file_record(name) == built[name], 'caller selected wrong macro dylib')
    return dict(outputs=rows,depinfo=dict(path=str(dep),**dep_row),default_discovered=selected)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--prerequisite-sha256',required=True); args = parser.parse_args()
    require(Path(__file__) == SOURCE/'run_once.py' and Path.cwd() == ROOT, 'exact runner path and cwd')
    require(not os.path.lexists(WORK) and not os.path.lexists(OUT), 'fresh work/results required')
    plan = read(SOURCE/'plan.json',PLAN_SHA)
    require(len(plan['commands']) == 20 and len(plan['cases']) == 9 and plan['actual_result'] is None,
            'fixed unrun semantic plan')
    require(plan['compiler'] == str(TC/'bin/rustc'), 'matched N compiler only')
    # Validate literal presence without consuming a future success claim.
    require(re.fullmatch('[0-9a-f]{64}',args.prerequisite_sha256) is not None
            and args.prerequisite_sha256 == plan['prerequisite']['sha256'], 'actual reviewed prerequisite SHA required')
    guard(entry=True); OUT.mkdir(); WORK.mkdir()
    for arm in ['stock','candidate']:
        (WORK/'macro-tests'/arm/'tmp').mkdir(parents=True)
    shutil.copyfile(SOURCE/'run_once.py',OUT/'run_once.py'); shutil.copyfile(SOURCE/'plan.json',OUT/'plan.json')
    records=[]; summary=dict(status='waiting',started_at=time.time(),parent_pid=os.getpid(),plan_sha256=PLAN_SHA,
        prerequisite_sha256=args.prerequisite_sha256,command_records=records,children=0,signals=[],retries=0,
        default_discovery_qualified=False,compiler_distribution_qualified=False,runtime_composition_qualified=False,
        benchmark=False)
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
        before=source_readback(plan);write('inputs-before.json',before)
        qualified,prerequisite_before,previous_runtime=prerequisite(plan,args.prerequisite_sha256)
        write('prerequisite.json',qualified);write('prerequisite-before.json',prerequisite_before)
        inventory=read(SOURCE/'runtime-inventory.json',plan['runtime_inventory']['sha256'])
        compiled=read(inventory['compiled']['path'],inventory['compiled']['sha256'])
        require(compiled['stage1']==inventory['entries'] and compiled['source_identity']==inventory['source_identity'], 'old N compiler proof differs')
        runtime_before=runtime_readback(inventory,True);write('runtime-before.json',runtime_before)
        require(runtime_before==previous_runtime,'current N differs from successful predecessor')
        owned=create_overlays(plan,qualified['selected_artifacts'])
        overlay_before=overlay_readback(plan,owned);write('overlays-before.json',overlay_before)
        cases={case['name']:case for case in plan['cases']};compared={};built={}
        for index,spec in enumerate(plan['commands']):
            current=runtime_readback(inventory,False)
            require(current['entries']==runtime_before['entries'] and current['directories']==runtime_before['directories'], 'N runtime identity/membership changed')
            require(overlay_readback(plan,owned)==overlay_before,'overlay changed before child')
            require(all(file_record(name)==row for name,row in built.items()),'previously built artifact changed')
            label,record=run(index,spec,lock,records);summary['children']+=1
            observed=diagnostics(label,spec,cases);dep=dependency_proof(spec,built,owned)
            if spec['role']=='caller':
                key=spec['case']
                if spec['arm']=='stock':compared[key]=observed
                else:require(observed==compared[key],'stock/candidate stable diagnostics differ')
            if spec['expected_returncode']==0:built.update(dep['outputs'])
            require(all(file_record(name)==row for name,row in built.items()),'built artifact changed during child')
            require(overlay_readback(plan,owned)==overlay_before,'overlay changed during child')
            write(label+'-verification.json',dict(label=label,diagnostics=observed,dependency=dep));write('execution.json',summary,replace=True)
        after={name:file_record(name) for name in before};write('inputs-after.json',after)
        require(after==before,'source/provenance input changed')
        prior_after={name:file_record(name) for name in prerequisite_before};write('prerequisite-after.json',prior_after)
        require(prior_after==prerequisite_before,'completed predecessor changed')
        runtime_after=runtime_readback(inventory,True);write('runtime-after.json',runtime_after)
        require(runtime_after==runtime_before,'full N runtime changed')
        overlay_after=overlay_readback(plan,owned);write('overlays-after.json',overlay_after)
        require(overlay_after==overlay_before,'full overlay changed')
        write('built-artifacts.json',built)
        require(len(records)==20 and all(row['status']=='closed' and not row['may_be_live'] for row in records),'all children must close')
        summary.update(status='passed',default_discovery_qualified=True,finished_at=time.time(),
            free_bytes_after=guard(),work_and_results_bytes=work_size(),compared_cases=9,input_files=len(before),
            runtime_files=63,runtime_links=2,overlay_links=104,overlay_owned_files=8)
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
    write('result.json',dict(status='passed',children=20,macro_dylib_builds=2,caller_cases_per_arm=9,
        execution_sha256=file_record(OUT/'execution.json')['sha256'],prerequisite_sha256=args.prerequisite_sha256,
        inputs_unchanged=True,complete_N_runtime_unchanged=True,overlays_unchanged=True,
        default_discovery_qualified=True,real_N_external_client_integration=True,compiler_server_unchanged=True,
        builtin_quote_optimized=False,compiler_distribution_qualified=False,runtime_composition_qualified=False,
        holdout_qualified=False,benchmark=False))
    print(json.dumps(dict(status='passed',result_sha256=file_record(OUT/'result.json')['sha256'])))


if __name__ == '__main__':
    main()

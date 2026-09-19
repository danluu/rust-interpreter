"""Bind the ordinary std07 packet after a passed, closed installation audit.

This builder runs no subprocess, acquires no workload lock and walks no provider
or installed payload tree. It preserves the unbound plan before publishing the
bound plan, inputs and unexecuted launch. Any partial write remains evidence.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
HERE = ROOT/'experiments/runtime-std-after-installation07-01'
OLD = R/'experiments/runtime-compiler-installation/std-01'
SELF = X/'.work/bind_runtime_std07_packet_02.py'
HANDOFF = X/'.work/runtime-std-after-installation07-source-handoff-03.json'
HANDOFF_SHA = '0531e5b9a3acda643720293be0c99300d125346fb676ed0866436d6068733350'
UNBOUND_SHA = 'c985c339897ee443f21a763e48ccc94cbce450365051628b707e0d4dfa2a6128'
AUDIT = R/'.work/hir-options-hash-runtime-installation-independent-verification-07.json'
AUDIT_EXECUTION = ROOT/'.work/runtime13-saved-audit-installation-execution-01'
RECEIPT = R/'.work/hir-options-hash-runtime-installation-07/receipt.json'
REPORT = X/'.work/runtime-std07-packet-binding-01.json'
SUPERVISOR = 'hir-options-hash-runtime-std-supervisor-07-01'
MAX_FILE = 32*2**20
MAX_RETAINED = 64*2**20
OBSERVED = {}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def sha_value(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'explicit actual SHA remains unbound')
    return value


def stamp(value):
    return [value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink]


def file(path, expected=None, *, payload=False, remember=True):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.resolve(strict=True) == path,
            'ordinary canonical binding input required: '+str(path))
    before = stamp(path.lstat())
    require(stat.S_ISREG(before[2]) and 0 <= before[3] <= MAX_FILE,
            'bounded ordinary binding input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    digest = hashlib.sha256(); chunks = []
    with os.fdopen(fd, 'rb') as stream:
        require(stamp(os.fstat(stream.fileno())) == before, 'opened input differs')
        total = 0
        while block := stream.read(1024*1024):
            total += len(block); require(total <= MAX_FILE, 'binding input grew')
            digest.update(block)
            if payload:
                chunks.append(block)
        require(stamp(os.fstat(stream.fileno())) == before, 'input changed during full read')
    require(total == before[3] and stamp(path.lstat()) == before
            and path.resolve(strict=True) == path, 'binding input changed after read')
    row = dict(path=str(path), sha256=digest.hexdigest(), bytes=total, identity=before)
    if expected is not None:
        require(row['sha256'] == sha_value(expected), 'binding input SHA differs: '+str(path))
    if remember:
        require(str(path) not in OBSERVED or same(OBSERVED[str(path)], row),
                'binding input changed after first observation: '+str(path))
        OBSERVED.setdefault(str(path), row)
    return b''.join(chunks) if payload else row


def read(path, expected=None):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            require(key not in value, 'duplicate binding JSON key'); value[key] = child
        return value
    return json.loads(file(path, expected, payload=True), object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def reference(value, path):
    require(type(value) is dict and set(value) == {'path', 'sha256'}
            and value['path'] == str(path), 'exact binding reference route required')
    return sha_value(value['sha256'])


def fresh(paths):
    for path in paths:
        require(not os.path.lexists(path), 'fresh binding/output route required: '+str(path))


def recheck():
    for row in list(OBSERVED.values()):
        file(row['path'], row['sha256'])


def write(path, payload):
    with Path(path).open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    result = file(path, hashlib.sha256(payload).hexdigest(), remember=False)
    require(result['identity'][6] == 1, 'binding output is not an independent file')
    return result


def closed_installation(invocation):
    """First gate: only named audit report/execution/raw files are read here."""
    report_sha = reference(invocation['installation_audit'], AUDIT)
    execution_sha = reference(invocation['installation_audit_execution'], AUDIT_EXECUTION/'record.json')
    audit = read(AUDIT, report_sha)
    execution = read(AUDIT_EXECUTION/'record.json', execution_sha)
    require(audit['status'] == 'verified' and audit['phase'] == 'installation'
            and audit['saved_audit_source'] == str(ROOT/'experiments/hir-options-hash-runtime-audit-13'),
            'passed installation audit required')
    require(execution['status'] == 'finished' and execution['mode'] == 'audit'
            and execution['phase'] == 'installation' and type(execution['returncode']) is int
            and execution['returncode'] == 0 and execution['may_be_live'] is False
            and execution['observation_errors'] == [] and 'execution_error' not in execution
            and execution['report'] == str(AUDIT) and execution['result_sha256'] == report_sha
            and execution['pid'] == audit['pid'] and execution['parent_pid'] == audit['parent_pid'],
            'closed actual audit execution association required')
    times = [execution['started_at'], audit['started_at'],
             audit['finished_at'], execution['finished_at'], execution['canonical_released_at']]
    require(all(type(value) in (int, float) and 0 < value <= time.time() for value in times)
            and times == sorted(times), 'actual audit closure chronology differs')
    require(file(AUDIT_EXECUTION/'stderr', execution['stderr_sha256'], payload=True) == b'',
            'successful audit stderr must be empty')
    require(same(read(AUDIT_EXECUTION/'stdout', execution['stdout_sha256']),
                 dict(status='verified', path=str(AUDIT), sha256=report_sha)),
            'actual audit stdout report binding differs')
    return audit


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--invocation', type=Path, required=True)
    parser.add_argument('--invocation-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == R and sys.dont_write_bytecode and sys.flags.optimize == 0,
            'fixed owner and unoptimized Python -B required')
    observed_before = dict(os.environ)
    invocation = read(args.invocation, sha_value(args.invocation_sha256))
    require(invocation['status'] == 'reviewed-std07-packet-binding'
            and invocation['observed_environment'] is None
            and invocation['std_execution'] is False and invocation['admission_authorized'] is False,
            'binding invocation is unreviewed or invents observations')
    file(SELF, reference(invocation['builder'], SELF))
    require(Path(__file__).resolve(strict=True) == SELF, 'exact reviewed builder required')
    require(reference(invocation['source_handoff'], HANDOFF) == HANDOFF_SHA,
            'reviewed std source handoff differs')
    require(reference(invocation['unbound_plan'], HERE/'plan.json') == UNBOUND_SHA,
            'exact original unbound plan required')
    require(invocation['output_inputs'] == str(HERE/'inputs.json')
            and invocation['output_launch'] == str(HERE/'launch.json')
            and invocation['binding_report'] == str(REPORT), 'binding publication routes differ')
    outputs = [HERE/'inputs.json', HERE/'launch.json', HERE/'plan.unbound-01.json',
               HERE/'plan.binding-01.tmp', REPORT]
    future_work = [R/'.work/hir-options-hash-runtime-std-supervision-07-01',
        R/'.work/hir-options-hash-runtime-std-07-01', R/'.work/experiments'/SUPERVISOR,
        R/'.work/hir-options-hash-runtime-std-launch-execution-07-01']
    fresh(outputs+future_work)
    # No runtime prefix or selected-module import is reached until this closes.
    audit = closed_installation(invocation)
    handoff = read(HANDOFF, HANDOFF_SHA)
    for row in handoff['sources'].values():
        require(same(file(row['path'], row['sha256']), row), 'reviewed source identity differs')
    unbound = file(HERE/'plan.json', UNBOUND_SHA, payload=True)
    plan = json.loads(unbound)
    original = read(OLD/'plan.json', handoff['predecessors']['plan']['sha256'])
    old_freeze = read(OLD/'inputs.json', handoff['predecessors']['inputs']['sha256'])
    file(OLD/'prepare.py', handoff['predecessors']['prepare']['sha256'])
    selection = read(HERE/'selection.json')
    require(selection['ordinary_script_paths'] == sorted(path for path in old_freeze['files']
            if Path(path).parent == R/'scripts' and Path(path).suffix == '.py'),
            'original finite script scope differs')
    source_paths = set(selection['ordinary_script_paths'])
    source_paths.update(row['path'] for row in selection['modules'].values())
    source_paths.update(str(HERE/name) for name in
        ['imports.py', 'prepare.py', 'std_cli.py', 'test_adapter.py', 'selection.json', 'README.md'])
    source_paths.update(map(str, [SELF, args.invocation, HANDOFF, OLD/'plan.json',
                                 OLD/'inputs.json', OLD/'prepare.py']))
    for path in sorted(source_paths):
        file(path)
    for row in selection['modules'].values():
        file(row['path'], row['sha256'])

    key = sha_value(invocation['runtime_key'])
    phase = audit['phase_result']; prefix = R/'.work/runtime-compilers'/key
    require(phase['runtime_key'] == key and phase['sysroot'] == str(prefix/'sysroot'),
            'actual audited runtime key differs')
    for role, filename, field in [('runtime_readiness', 'ready.json', 'ready_sha256'),
            ('runtime_admission', 'admission.json', 'admission_sha256'),
            ('runtime_qualification', 'qualification.json', 'qualification_sha256')]:
        expected = reference(invocation[role], prefix/filename)
        require(expected == phase[field], 'actual audited publication SHA differs')
        read(prefix/filename, expected)
        plan[role] = dict(invocation[role])
    plan['runtime_key'] = key
    plan['runtime_installation_audit'] = dict(invocation['installation_audit'])
    plan['runtime_installation_receipt'] = dict(path=str(RECEIPT), sha256=audit['receipt_sha256'])
    read(RECEIPT, audit['receipt_sha256'])
    plan['runtime_installation_audit_execution'] = dict(invocation['installation_audit_execution'])

    passed = invocation['passed_environment']
    require(type(passed) is dict and all(type(k) is str and type(v) is str for k,v in passed.items())
            and set(passed) == set(original['environment'])
            and all(passed[k] == v for k,v in original['environment'].items()
                    if k != '__CF_USER_TEXT_ENCODING')
            and re.fullmatch('0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+:0x[0-9A-Fa-f]+',
                             passed['__CF_USER_TEXT_ENCODING']) is not None
            and same(observed_before, passed), 'exact reviewed passed/observed std environment differs')
    spec = importlib.util.spec_from_file_location('_std07_binding_factory', HERE/'imports.py')
    factory = importlib.util.module_from_spec(spec);sys.modules[spec.name] = factory;spec.loader.exec_module(factory)
    def checked_source(path):
        require(str(path) in OBSERVED, 'undeclared binding import/proof')
        return file(path, OBSERVED[str(path)]['sha256'])['sha256']
    modules = factory.definitions(checked_source)
    factory.runtime_proof(plan, checked_source)
    with factory.aliases(modules.public_aliases):
        modules.std.validate_environment(passed)
        identity = modules.runtime.identity_for(read(prefix/'admission.json')['identity']['admission'])
        ready = read(prefix/'ready.json')
        require(same(identity, ready['identity']) and modules.runtime.digest(identity) == key,
                'audited runtime identity reconstruction differs')
        commit = identity['provenance']['source_commit']
        require(same(identity['provenance']['std_source_paths'], modules.std.source_capability(commit)),
                'qualified std source-path capability required')
        source_prefix = modules.std.SOURCE
        source_files = {name[len(source_prefix):]: value for name,value in identity['files'].items()
                        if name.startswith(source_prefix)}
        require(all(name in source_files for name in modules.std.REQUIRED_SOURCES)
                and modules.runtime.digest({source_prefix+n: h for n,h in source_files.items()})
                    == identity['source_sha256'], 'audited standard-source inventory differs')
        sizes = {}
        for name in source_files:
            saved = ready['stamps'][source_prefix+name]
            require(type(saved) is list and len(saved) == 6
                    and all(type(value) is int and value >= 0 for value in saved)
                    and stat.S_ISREG(saved[2]) and not saved[2] & 0o222,
                    'audited source size/mode record differs')
            sizes[name] = saved[3]
        require({name for name,value in ready['stamps'].items()
                 if name.startswith(source_prefix) and stat.S_ISREG(value[2])}
                == {source_prefix+name for name in source_files}, 'audited source size coverage differs')
        platform = modules.cargo.platform_identity()
        developer = Path(passed['DEVELOPER_DIR'])
        require(developer.is_dir() and developer.resolve(strict=True) == developer,
                'canonical selected developer directory required')
        configuration = modules.std.configuration(R, passed)
        for path, value in configuration.items():
            if value is not None:
                file(path, value['sha256']);source_paths.add(path)
        executors = {}
        for path in sorted(original['executors']):
            logical = Path(path); before = modules.toolchain._stamp(logical)
            link = os.readlink(logical) if logical.is_symlink() else None
            resolved = Path(before[0]); observed = file(resolved)
            require(modules.toolchain._stamp(logical) == before
                    and (os.readlink(logical) if logical.is_symlink() else None) == link,
                    'executor route changed during observation')
            executors[path] = dict(stamp=before, sha256=observed['sha256'], link_text=link)
            source_paths.add(str(resolved))
        python_path = Path('/opt/homebrew/bin/python3')
        python = dict(path=str(python_path), resolved=executors[str(python_path)]['stamp'][0],
                      sha256=executors[str(python_path)]['sha256'])
        require(str(Path(sys.executable).resolve(strict=True)) == python['resolved'],
                'actual binder Python route differs')
        require(original['cargo_executable'] == plan['cargo_executable']
                and executors[plan['cargo_executable']]['sha256']
                    == original['executors'][plan['cargo_executable']]['sha256'],
                'reviewed Cargo recipe executable differs')
        observed_after_imports = dict(os.environ)
        require(same(observed_after_imports, passed), 'imports changed the exact std environment')
        plan.update(status='prepared-unexecuted', environment=passed, configuration=configuration,
            executors=executors, platform=platform, compiler_source_commit=commit,
            binding_invocation=dict(path=str(args.invocation), sha256=args.invocation_sha256))
        plan['bounds'].update(standard_source_files=len(source_files), standard_source_bytes=sum(sizes.values()))
        plan['command'][6] = key
        for name in ['cargo_recipe','expected_outer_cli_children','canonical_lock','namespace',
                     'lock_wait_seconds','lock_ownership']:
            require(same(plan[name], original[name]), 'ordinary std contract changed: '+name)
        # Recheck first observations while the same selected aliases remain active.
        require(same(modules.std.configuration(R, passed), configuration)
                and same(modules.cargo.platform_identity(), platform), 'binding configuration/platform changed')
        for path, row in executors.items():
            logical = Path(path)
            require(modules.toolchain._stamp(logical) == row['stamp']
                    and (os.readlink(logical) if logical.is_symlink() else None) == row['link_text'],
                    'binding executor route changed')
    require(same(dict(os.environ), passed), 'binding environment changed')

    source_paths.update(str(path) for path in [AUDIT, AUDIT_EXECUTION/'record.json',
        AUDIT_EXECUTION/'stdout', AUDIT_EXECUTION/'stderr', RECEIPT,
        prefix/'ready.json', prefix/'admission.json', prefix/'qualification.json'])
    plan_bytes = encoded(plan)
    retained = {path: OBSERVED[path] for path in sorted(source_paths)}
    retained[str(HERE/'plan.json')] = dict(sha256=hashlib.sha256(plan_bytes).hexdigest(), bytes=len(plan_bytes))
    retained[str(HERE/'plan.unbound-01.json')] = dict(sha256=UNBOUND_SHA, bytes=len(unbound))
    require(all(value['bytes'] <= MAX_FILE for value in retained.values())
            and sum(value['bytes'] for value in retained.values()) <= MAX_RETAINED,
            'ordinary std retained-input limit exceeded')
    frozen = dict(schema_version=1, owner=str(R), files={p:v['sha256'] for p,v in retained.items()},
                  file_count=len(retained), input_bytes=sum(v['bytes'] for v in retained.values()), python=python)
    frozen_bytes = encoded(frozen);frozen_sha = hashlib.sha256(frozen_bytes).hexdigest()
    factory.validate_plan(plan, frozen_sha)
    launch = dict(schema_version=1, status='unexecuted', owner=str(R), cwd=str(R),
        command=[str(python_path),'-B',str(R/'scripts/supervise_experiment.py'),'--run-id',SUPERVISOR,
                 '--',str(python_path),'-B',str(HERE/'prepare.py'),'--frozen-sha',frozen_sha],
        environment=passed, python=python, source_freeze=dict(path=str(HERE/'inputs.json'),sha256=frozen_sha),
        helper=dict(path=str(HERE/'prepare.py'),sha256=OBSERVED[str(HERE/'prepare.py')]['sha256']),
        plan=dict(path=str(HERE/'plan.json'),sha256=hashlib.sha256(plan_bytes).hexdigest()),
        runtime_key=key, canonical_lock=plan['canonical_lock'], bounds=plan['bounds'],
        wait_seconds=600, expected_direct_cli_children=7, review_required_before_launch=True)
    recheck();fresh(outputs+future_work)
    saved = write(HERE/'plan.unbound-01.json', unbound)
    write(HERE/'plan.binding-01.tmp', plan_bytes)
    file(HERE/'plan.json', UNBOUND_SHA)
    os.replace(HERE/'plan.binding-01.tmp', HERE/'plan.json')
    plan_row = file(HERE/'plan.json', hashlib.sha256(plan_bytes).hexdigest(), remember=False)
    inputs_row = write(HERE/'inputs.json', frozen_bytes)
    launch_row = write(HERE/'launch.json', encoded(launch))
    for path, expected in frozen['files'].items():
        file(path, expected, remember=path != str(HERE/'plan.json'))
    fresh(future_work)
    require(same(modules.std.configuration(R, passed), configuration)
            and same(modules.cargo.platform_identity(), platform), 'published context changed')
    for path, row in executors.items():
        logical = Path(path)
        require(modules.toolchain._stamp(logical) == row['stamp']
                and (os.readlink(logical) if logical.is_symlink() else None) == row['link_text'],
                'published executor route changed')
    require(same(dict(os.environ), passed), 'environment changed after binding publication')
    result = dict(status='bound-unexecuted-std07-packet', pid=os.getpid(), parent_pid=os.getppid(),
        finished_at=time.time(), invocation=dict(path=str(args.invocation),sha256=args.invocation_sha256),
        installation_audit=invocation['installation_audit'], installation_audit_execution=invocation['installation_audit_execution'],
        passed_environment=passed, observed_before=observed_before, observed_after_imports=observed_after_imports,
        observed_after_publication=dict(os.environ), source_observations=OBSERVED,
        source_observation_scope='First current rows; original plan row is the preserved unbound predecessor. Actual bound plan is recorded separately.',
        source_sizes=dict(files=len(sizes), bytes=sum(sizes.values()), copies=2,
                          copy_bytes=2*sum(sizes.values()), basis='audited ready identity/stamps; no payload walk'),
        saved_unbound_plan=saved, plan=plan_row, inputs=inputs_row, launch=launch_row,
        file_count=frozen['file_count'], retained_input_bytes=frozen['input_bytes'],
        compiler_calls=0, inspector_calls=0, provider_payload_walk=False, std_execution=False,
        pure12_scope='development selection tests only; no std or runtime qualification claim')
    result_row = write(REPORT, encoded(result))
    print(json.dumps(dict(status=result['status'],report=result_row,inputs=inputs_row,launch=launch_row),sort_keys=True))


if __name__ == '__main__':
    main()

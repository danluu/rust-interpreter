#!/usr/bin/env python3
"""Freeze strict Ruff correctness from the retained diagnostic; no workload."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import tomllib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as a
from runtime_compiler import load_runtime_compiler
from runtime_tools import validate_tool_runtime
from interpreter import installed_tools
from std_mir_source_paths import load as load_std, namespace_for


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def reference(path):
    return dict(path=str(path), sha256=sha(path))


def write(path, value):
    with path.open('x') as output:
        output.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    a.require(Path.cwd() == a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
              'fixed owner/unoptimized Python -B required')
    old_plan = HERE.parent / 'ruff-diagnostic-01/plan.json'
    old_freeze = HERE.parent / 'ruff-diagnostic-01/inputs.json'
    old = a.read(old_plan)
    compiler = load_runtime_compiler(a.R_OWNER, a.RUNTIME_KEY)
    tools, key = installed_tools(a.TOOL_KEY)
    validate_tool_runtime(tools, key, compiler)
    a.require(a.read(tools / 'compiler.json') == old['runtime_composition'], 'published composition differs')
    for proof in [old['tool_publication'], old['published_tools'], old['source_inventory'], old['source_acquisition']]:
        a.require(sha(proof['path']) == proof['sha256'], 'prior source/tool provenance differs')
    prior_receipt = a.OWNER / '.work/ruff-hir-diagnostic-supervision-01/receipt.json'
    a.require(a.read(prior_receipt)['status'] == 'passed', 'completed diagnostic required')
    prior_records = a.R_OWNER / '.work/runs/runtime-ruff-hir-diagnostic-01/records.json'
    old_rows = a.read(prior_records)
    original = (a.SOURCE / a.WORKFLOWS['ruff']['file']).read_bytes()
    inventory = a.read(old['source_inventory']['path'])
    a.require(hashlib.sha256(original).hexdigest() == inventory[a.WORKFLOWS['ruff']['file']]['sha256'],
              'Ruff source is not restored')
    states, schedule = a.history(original)
    retained_custom = [row for row in old_rows if row['mode'] != 'native']
    a.require(len(retained_custom) == len(schedule) == 16, 'prior custom history differs')
    for spec, prior in zip(schedule, retained_custom):
        a.require(all(spec[field] == prior[field] for field in ['state', 'phase', 'mode', 'source_sha256'])
                  and prior['tests'] == a.WORKFLOWS['ruff']['tests'], 'source/test/order differs from diagnostic')
    environment = dict(old['environment'], TMPDIR=str(a.WORK / 'tmp') + '/',
                       CARGO_TERM_COLOR='never', RUST_INTERP_LAUNCH_STATS='1')
    a.require(not any(name in environment for name in a.FORBIDDEN), 'compatibility policy in strict environment')
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment)
    try:
        standard = load_std(a.R_OWNER, a.STD_KEY, compiler,
                           namespace_for('source-paths-v2-shared', 'unused-shared-policy'))
    finally:
        os.environ.clear()
        os.environ.update(saved)
    config_paths = set(map(Path, old['configuration']))
    for root in [a.WORK, a.WORK / 'cache', a.WORK / 'cache/baseline', a.WORK / 'cache/candidate']:
        config_paths.update(ancestor / '.cargo' / name for ancestor in [root, *root.parents]
                            for name in ['config', 'config.toml'])
    configuration = {}
    for path in sorted(config_paths):
        a.require(not path.is_symlink() and all(not parent.is_symlink() for parent in path.parents),
                  'indirect strict configuration route')
        row = dict(exists=path.exists())
        if path.exists():
            a.require(path.is_file(), 'configuration is not a file')
            row['sha256'] = sha(path)
            if path.name in ['config', 'config.toml'] and path.parent.name == '.cargo':
                policies = tomllib.loads(path.read_text()).get('env', {})
                a.require(not any(name in policies for name in a.FORBIDDEN), 'Cargo config enables compatibility policy')
        configuration[str(path)] = row
    providers = {name: a.provider(name) for name in old['providers']}
    a.require(all(row['sha256'] == old['providers'][name]['sha256'] for name, row in providers.items()),
              'provider bytes differ from qualified diagnostic')
    executors = {name: a.provider(name) for name in old['executors']}
    python = Path('/opt/homebrew/bin/python3')
    producer_files = [*sorted((a.R_OWNER / 'scripts').glob('*.py')),
        HERE / 'run.py', HERE / 'prepare.py', HERE / 'README.md',
        HERE.parent / 'runtime_admission_v2.py', HERE.parent / 'run_ruff_diagnostic.py',
        HERE.parent / 'ruff-profile-02/profile_helpers.py',
        a.OWNER / 'experiments/stable-cgu/owned_stage.py', a.OWNER / 'scripts/supervise_experiment.py']
    commands = [dict(label=spec['label'], command=a.command(str(python), spec), cwd=str(a.R_OWNER),
                     expected_returncode=1 if spec['state'] == -1 else 0) for spec in schedule]
    plan = dict(schema_version=1, status='unexecuted', name=a.NAME, policy=a.POLICY,
        owner=str(a.OWNER), runtime_owner=str(a.R_OWNER), runtime_key=a.RUNTIME_KEY, std_key=a.STD_KEY,
        tool_key=key, runtime_composition=old['runtime_composition'], tool_publication=old['tool_publication'],
        published_tools=old['published_tools'], source_inventory=old['source_inventory'],
        source_acquisition=old['source_acquisition'], prior_diagnostic=reference(prior_receipt),
        prior_records=reference(prior_records), historical_plan=reference(old_plan),
        python=str(python), launch_environment=environment, child_environment=environment,
        platform=list(os.uname()), executor_routes=executors, providers=providers,
        provider_directories=old['provider_directories'], configuration=configuration,
        producer_sources={str(path): sha(path) for path in producer_files},
        canonical_lock=old['canonical_lock'], wait_seconds=600, history=schedule, commands=commands,
        allocated_byte_limit=6 * 2**30,
        bounds=dict(entry_free_gib=16, active_child_stop_gib=9, running_floor_gib=8,
                    retained_inputs_bytes=96 * 2**20, retained_input_file_bytes=32 * 2**20),
        changes_from_diagnostic=['Remove trap-unsupported-calls and run-try-callbacks.',
            'Use two fresh owned custom target caches and retain actual compiler argv plus selected dep-info.',
            'Execute the same 16 ordinary custom launcher calls directly; omit all native application calls.'],
        scope='Strict JIT six-test batch compatibility with HIR off/on; instrumentation retained; no latency qualification.',
        performance_qualified=False, benchmark=False, no_new_native_application_baseline=True,
        policy_proof='Exact environment, launcher flags/stats, selected export dep-info with both variables unset, and absent .calls.json.',
        compiler_proof_limit='Wrapper argv records plus selected export metadata; no invented nested process ancestry.',
        sdk_proof_limit='Selected executors/rustc driver/LLVM/objcopy and Xcode SDK provider files/routes; no full SDK header inventory.')
    destination = HERE / 'plan'
    a.require(not destination.exists() and not a.WORK.exists(), 'strict plan/output must be fresh')
    destination.mkdir()
    write(destination / 'plan.json', plan)
    files = set(map(Path, a.read(old_freeze)['files'])) | set(producer_files)
    files.update([destination / 'plan.json', old_plan, old_freeze, prior_receipt, prior_records])
    files.update(Path(name) for name, row in configuration.items() if row['exists'])
    a.require(all(path.resolve(strict=True) == path and path.is_file()
                  and path.stat().st_size <= 32 * 2**20 for path in files), 'ordinary bounded frozen files required')
    total = sum(path.stat().st_size for path in files)
    a.require(total <= 96 * 2**20, 'strict input retention bound exceeded')
    frozen = dict(schema_version=1, owner=str(a.OWNER),
        python=dict(resolved=str(python.resolve()), sha256=sha(python)),
        files={str(path): sha(path) for path in sorted(files)})
    write(destination / 'inputs.json', frozen)
    # Exercise the actual read-only API boundary before a workload is reviewed.
    probe = a.Admission.__new__(a.Admission)
    probe.plan_path, probe.freeze_path = destination / 'plan.json', destination / 'inputs.json'
    probe.freeze_sha = sha(probe.freeze_path)
    probe.plan, probe.freeze, probe.source_files = plan, frozen, plan['producer_sources']
    probe.compiler, probe.tools, probe.key, probe.standard = compiler, tools, key, standard
    probe.environment = environment
    started = time.time()
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment)
    try:
        probe.guard()
    finally:
        os.environ.clear()
        os.environ.update(saved)
    write(destination / 'metadata-preflight.json', dict(status='passed', started_at=started, finished_at=time.time(),
        pid=os.getpid(), source_freeze_sha256=sha(probe.freeze_path), workload_children=0, work_directory_created=False))
    launch = dict(owner=str(a.OWNER), cwd=str(a.OWNER), environment=environment,
        helper=reference(HERE / 'run.py'), plan=reference(probe.plan_path), source_freeze=reference(probe.freeze_path),
        command=[str(python), '-B', str(a.OWNER / 'scripts/supervise_experiment.py'), '--run-id',
                 'ruff-runtime-strict-supervisor-01', '--', str(python), '-B', str(HERE / 'run.py'),
                 '--plan', str(probe.plan_path), '--freeze', str(probe.freeze_path),
                 '--freeze-sha256', sha(probe.freeze_path)],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, bounds=plan['bounds'], expected_children=16,
        review_required_before_launch=True)
    write(destination / 'launch.json', launch)
    print(json.dumps(dict(launch=reference(destination / 'launch.json'), plan=reference(probe.plan_path),
                         freeze=reference(probe.freeze_path), input_files=len(files), input_bytes=total), indent=2))


if __name__ == '__main__':
    main()

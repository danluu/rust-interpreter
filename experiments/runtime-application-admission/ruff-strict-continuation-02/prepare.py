#!/usr/bin/env python3
"""Freeze a 2-saved + 14-new strict history; read-only prerequisites, no workload."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as a
import retained
import runtime_platform
from saved_history import verify
from runtime_compiler import load_runtime_compiler
from runtime_tools import validate_tool_runtime
from interpreter import installed_tools
from std_mir_source_paths import load as load_std, namespace_for


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reference(path):
    return dict(path=str(path), sha256=sha(path))


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def floor(*_):
    free = shutil.disk_usage(a.OWNER).free
    a.require(free >= 9*2**30, 'continuation preparation free-space floor')
    return free


def main():
    a.require(Path.cwd() == a.OWNER and sys.dont_write_bytecode and not sys.flags.optimize,
              'fixed owner and unoptimized Python -B required')
    prior = HERE.parent / 'ruff-strict-03/plan'
    a.require(sha(prior/'launch.json') == '80f9c3a302d152c1b6d1fc3fbdc255645ac357d952f7da19a01b64ef4d6072c6'
              and sha(prior/'inputs.json') == '68b65041721689128e4da3115d2c7f00e93cc785789ab8d5ac76226666cf15b2'
              and sha(prior/'plan.json') == 'aceb41e3050c6552c11eedc94cd8564e708e190f04aa9b1b8e1f1bf7ce139f35',
              'failed strict03 proposal changed')
    old = a.read(prior/'plan.json')
    old_freeze = a.read(prior/'inputs.json')
    for name, digest in old_freeze['files'].items():
        floor()
        a.require(Path(name).resolve(strict=True) == Path(name) and sha(name) == digest,
                  'prior input changed; continuation does not readmit bytes: '+name)
    editable = a.SOURCE / a.WORKFLOWS['ruff']['file']
    original_snapshot = a.PRIOR_WORK / 'inputs' / str(editable).lstrip('/')
    a.require(sha(editable) == sha(original_snapshot) == old_freeze['files'][str(editable)],
              'source was not restored to its retained original')
    mutable = [name for name in old_freeze['files'] if name == str(editable)
               or Path(name).is_relative_to(a.PRIOR_WORK/'cache')
               or Path(name).is_relative_to(a.PRIOR_WORK/'raw')
               or Path(name).is_relative_to(a.PRIOR_WORK/'artifacts')
               or Path(name).is_relative_to(a.PRIOR_WORK/'compiler-argv')
               or Path(name).is_relative_to(a.PRIOR_WORK/'tmp')]
    a.require(mutable == [str(editable)], 'unexpected immutable/mutable intersection')
    failed = a.PRIOR_WORK/'supervision.json'
    failure_audit = a.OWNER/'.work/ruff-strict-failure-independent-verification-03.json'
    a.require(sha(failed) == '9f9a46d02c0e91ca0cbaa26b07b66575bd44c3b2324826d4777aa04fad61cc16'
              and sha(failure_audit) == '6c2ac83019fd74cbd2195485955eb4a2981ce21cb413f7ed8e40b07c54d68960',
              'failed terminal/audit changed')
    before = old['platform_identity']
    observed = list(os.uname())
    a.require(runtime_platform.identity(observed) == before, 'kernel/machine identity changed')
    compiler = load_runtime_compiler(a.R_OWNER, a.RUNTIME_KEY)
    tools, key = installed_tools(a.TOOL_KEY)
    validate_tool_runtime(tools, key, compiler)
    a.require(a.read(tools/'compiler.json') == old['runtime_composition'], 'runtime composition changed')
    environment = dict(old['child_environment'], TMPDIR=str(a.WORK/'tmp')+'/')
    saved_env = dict(os.environ)
    os.environ.clear(); os.environ.update(environment)
    try:
        standard = load_std(a.R_OWNER, a.STD_KEY, compiler,
                            namespace_for('source-paths-v2-shared', 'unused-shared-policy'), rehash=True)
    finally:
        os.environ.clear(); os.environ.update(saved_env)
    a.require({name:a.provider(name) for name in old['providers']} == old['providers']
              and {name:a.provider(name) for name in old['executor_routes']} == old['executor_routes'],
              'strict provider/route/stamp changed')
    configuration = dict(old['configuration'])
    for root in [a.WORK, a.WORK/'tmp', a.WORK/'compiler-argv']:
        for parent in [root, *root.parents]:
            for suffix in ['config', 'config.toml']:
                path = parent/'.cargo'/suffix
                a.require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents),
                          'indirect continuation config route')
                row = dict(exists=path.exists())
                if row['exists']: row['sha256'] = sha(path)
                if str(path) in configuration:
                    a.require(row == configuration[str(path)], 'existing configuration changed')
                else:
                    a.require(not row['exists'], 'unexpected new continuation configuration')
                    configuration[str(path)] = row
    incomplete = HERE.parent/'ruff-strict-continuation-01'
    a.require(not (incomplete/'plan/launch.json').exists()
              and not (a.OWNER/'.work/ruff-runtime-strict-continuation-01').exists(),
              'incomplete read-only proposal unexpectedly launched')
    for part, skip in [('prior-evidence-inventory.json', ('cache',)), ('prior-cache-inventory.json', ())]:
        root = a.PRIOR_WORK if skip else a.PRIOR_WORK/'cache'
        retained.verify(root, a.read(incomplete/'plan'/part), skip=skip, floor=floor)
    destination = HERE/'plan'
    a.require(not destination.exists() and not a.WORK.exists() and not a.WORK.is_symlink(),
              'continuation plan/work must be fresh')
    destination.mkdir()
    evidence = retained.tree(a.PRIOR_WORK, skip=('cache',), floor=floor)
    cache = retained.tree(a.PRIOR_WORK/'cache', floor=floor)
    write(destination/'prior-evidence-inventory.json', evidence)
    write(destination/'prior-cache-inventory.json', cache)
    a.require(all(sha(destination/name) == sha(incomplete/'plan'/name)
                  for name in ['prior-evidence-inventory.json', 'prior-cache-inventory.json']),
              'successor inventory bytes differ from incomplete preparation01')
    states, schedule = a.history(original_snapshot.read_bytes())
    a.require(schedule == old['history'] and len(schedule) == 16
              and [row['state'] for row in schedule[:2]] == [0,0], 'continuation history differs')
    commands = [dict(label=spec['label'], command=a.command(old['python'], spec), cwd=str(a.R_OWNER),
                     expected_returncode=1 if spec['state'] == -1 else 0) for spec in schedule[2:]]
    for new, previous in zip(commands, old['commands'][2:], strict=True):
        expected = dict(previous, command=[arg.replace(str(a.PRIOR_WORK/'compiler-argv'),
                                                     str(a.WORK/'compiler-argv')) for arg in previous['command']])
        a.require(new == expected, 'remaining command changed beyond its new evidence namespace')
    producer_files = [*sorted((a.R_OWNER/'scripts').glob('*.py')),
        *[HERE/name for name in ['run.py','prepare.py','retained.py','saved_history.py','README.md','successor-from-strict03.diff']],
        *[HERE.parent/name for name in ['runtime_admission_v3.py','runtime_platform.py','run_ruff_diagnostic.py']],
        HERE.parent/'ruff-profile-02/profile_helpers.py',
        a.OWNER/'experiments/stable-cgu/owned_stage.py', a.OWNER/'scripts/supervise_experiment.py']
    plan = dict(old)
    plan.update(name=a.NAME, policy=a.POLICY, status='unexecuted', platform=observed,
        launch_environment=environment, child_environment=environment, configuration=configuration,
        producer_sources={str(path):sha(path) for path in producer_files}, commands=commands,
        prior_failed_terminal=reference(failed), prior_failure_audit=reference(failure_audit),
        prior_outer=reference(a.OWNER/'.work/experiments/ruff-runtime-strict-supervisor-03/status.json'),
        failed_plan=reference(prior/'plan.json'), failed_freeze=reference(prior/'inputs.json'),
        failed_launch=reference(prior/'launch.json'),
        prior_evidence_inventory=reference(destination/'prior-evidence-inventory.json'),
        prior_cache_inventory=reference(destination/'prior-cache-inventory.json'),
        editable_source=dict(path=str(editable), relative_path=a.WORKFLOWS['ruff']['file'],
            original_sha256=sha(original_snapshot), original_snapshot=reference(original_snapshot),
            policy='Each invocation binds the exact reviewed source-state digest; source restored on exit.'),
        saved_children=2, actual_continuation_children=14, complete_commands=16,
        aggregate_allocation_roots=[str(a.PRIOR_WORK),str(a.WORK)],
        incomplete_preparation=dict(source=str(incomplete),
            inputs=reference(incomplete/'plan/inputs.json'),
            inventory_representatives={name:dict(original=reference(incomplete/'plan'/name),
                retained_identical=reference(destination/name))
                for name in ['prior-evidence-inventory.json','prior-cache-inventory.json']},
            observation=reference(a.OWNER/'.work/ruff-strict-continuation-preparation-observation-01.json'),
            diagnosis=reference(a.OWNER/'.work/ruff-strict-continuation-preparation-diagnosis-01.json'),
            status='incomplete-read-only-preparation-no-workload',
            correction='Normalize custom_compiler.file_digest argument to Path; distinct continuation02 namespace.'),
        changes_from_failed_strict03=['Preserve original failed two-call terminal and artifacts.',
            'Reuse exact primed caches/namespaces; execute only remaining14 calls.',
            'Replace accidental immutable registry.rs freeze with saved original plus per-state digest.',
            'New controller/evidence/TMPDIR namespace; aggregate6GiB across both stages.'],
        historical_source_review=dict(reference=old['hostname_source_review'],
            editable_source_role='Historical original bytes; actual mutable path guarded by per-state digest.'),
        scope='Continued strict JIT six-test batches in two HIR modes:2 saved primes+14 new calls. Instrumented correctness only.')
    # Replace misleading inherited description about creating fresh caches.
    plan.pop('changes_from_diagnostic')
    write(destination/'plan.json', plan)
    files = set(map(Path, old_freeze['files'])) - {editable}
    files.update(producer_files)
    files.update(path for path in incomplete.iterdir() if path.is_file())
    files.update([incomplete/'plan/inputs.json', incomplete/'plan/plan.json',
        a.OWNER/'.work/ruff-strict-continuation-preparation-observation-01.json',
        a.OWNER/'.work/ruff-strict-continuation-preparation-diagnosis-01.json'])
    files.update([original_snapshot, prior/'plan.json', prior/'inputs.json', prior/'launch.json',
        prior/'metadata-preflight.json', failed, a.PRIOR_WORK/'result.json', failure_audit,
        a.OWNER/'.work/verify_ruff_strict_failure_03.py', a.OWNER/'.work/verify_ruff_strict_failure_03_v2.py',
        a.OWNER/'.work/launch_ruff_strict_03.py', destination/'plan.json',
        destination/'prior-evidence-inventory.json', destination/'prior-cache-inventory.json'])
    for root in [a.OWNER/'.work/experiments/ruff-runtime-strict-supervisor-03',
                 a.OWNER/'.work/ruff-strict-launch-execution-03']:
        files.update(root.iterdir())
    a.require(editable not in files and not any(path.is_relative_to(a.PRIOR_WORK/'cache') for path in files),
              'intentional mutable source/cache path frozen as immutable')
    a.require(all(path.resolve(strict=True) == path and path.is_file() and path.stat().st_size <= 32*2**20
                  for path in files), 'ordinary bounded continuation inputs required')
    total = sum(path.stat().st_size for path in files)
    a.require(total <= 96*2**20, 'continued source snapshot budget exceeded')
    frozen = dict(schema_version=1, owner=str(a.OWNER), python=old_freeze['python'],
                  files={str(path):sha(path) for path in sorted(files)})
    write(destination/'inputs.json', frozen)
    probe = a.Admission.__new__(a.Admission)
    probe.plan_path, probe.freeze_path = destination/'plan.json', destination/'inputs.json'
    probe.freeze_sha = sha(probe.freeze_path)
    probe.plan, probe.freeze, probe.source_files = plan, frozen, plan['producer_sources']
    probe.compiler, probe.tools, probe.key, probe.standard = compiler, tools, key, standard
    probe.environment, probe.owned = environment, SimpleNamespace(disk=floor)
    started = time.time()
    saved_env = dict(os.environ)
    os.environ.clear(); os.environ.update(environment)
    try:
        probe.guard(); probe.full_artifacts(); probe.prior_guard(full=True, cache=True)
        rows = verify(probe)
        inventory = a.read(plan['source_inventory']['path'])
        source = a.source_inventory(a.SOURCE, inventory, floor)
        capacity = probe.budget()
        a.require(len(rows) == 2 and source == a.read(a.PRIOR_WORK/'result.json')['source_restoration'],
                  'saved prime/source restoration readback differs')
    finally:
        os.environ.clear(); os.environ.update(saved_env)
    write(destination/'metadata-preflight.json', dict(status='passed', started_at=started, finished_at=time.time(),
        pid=os.getpid(), source_freeze_sha256=sha(probe.freeze_path), workload_children=0,
        work_directory_created=False, saved_children=2, remaining_children=14, capacity=capacity,
        source_inventory=source, full_runtime_std_tools_rehashed=True, unchanged_prior_inputs=True,
        mutable_guard_exception=[str(editable)], cache_admission_inventory=plan['prior_cache_inventory']))
    launch = dict(owner=str(a.OWNER), cwd=str(a.OWNER), environment=environment,
        helper=reference(HERE/'run.py'), plan=reference(probe.plan_path), source_freeze=reference(probe.freeze_path),
        command=[old['python'],'-B',str(a.OWNER/'scripts/supervise_experiment.py'),'--run-id',
            'ruff-runtime-strict-continuation-supervisor-02','--',old['python'],'-B',str(HERE/'run.py'),
            '--plan',str(probe.plan_path),'--freeze',str(probe.freeze_path),'--freeze-sha256',sha(probe.freeze_path)],
        canonical_lock=plan['canonical_lock'], wait_seconds=600, bounds=plan['bounds'], expected_children=14,
        saved_children=2, complete_commands=16, review_required_before_launch=True)
    write(destination/'launch.json', launch)
    print(json.dumps(dict(launch=reference(destination/'launch.json'), plan=reference(probe.plan_path),
        freeze=reference(probe.freeze_path), input_files=len(files), input_bytes=total), indent=2))


if __name__ == '__main__': main()

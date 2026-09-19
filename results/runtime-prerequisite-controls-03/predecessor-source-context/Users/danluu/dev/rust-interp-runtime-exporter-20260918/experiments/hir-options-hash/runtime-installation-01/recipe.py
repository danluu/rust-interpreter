"""Exact source-preflight and final installer cores using unchanged R policies.

The enclosing admitted controller supplies the existing monitored run, current
full input guard, and quick capacity guard. No CLI or implicit admission exists.
"""
import copy
from pathlib import Path


def require(value, message):
    if not value:
        raise RuntimeError(message)


def preflight_commands(q, candidate, owner, work, environment):
    runtime = q.runtime
    identity = runtime.identity_for(candidate)
    component = next(c for c in candidate['components'] if c['role'] == 'runtime')
    sysroot = Path(component['root'])
    compiler = runtime.RuntimeCompiler(runtime.digest(identity), sysroot, identity)
    env = compiler.environment(environment)
    return [dict(argv=argv, cwd=str(work), environment=env, expected=[1],
                 output=str(work/'commands'/str(index)))
            for index, argv in enumerate(q.probe_commands(compiler.rustc, sysroot, work))]


def execute_preflight(q, candidate, *, owner, work, environment, run, capacity, full_guard):
    full_guard()
    result = q.preflight(candidate, owner=owner, work=work, environment=environment,
                         run=run, guard=capacity)
    full_guard()
    require(result['status'] == 'passed' and len(result['commands']) == 2, 'two actual source probes required')
    result['full_current_guard_passed'] = True
    q.write_json(work/'result.json', result)
    return result


def final_specification(q, candidate, *, preflight_reference, preflight, policy_reference, policy):
    require(preflight['status'] == 'passed' and preflight['policy'] == q.PREFLIGHT
            and preflight.get('full_current_guard_passed') is True
            and preflight['candidate_sha256'] == q.runtime.digest(candidate)
            and len(preflight['commands']) == 2, 'actual candidate preflight required')
    spec = copy.deepcopy(candidate)
    commit = candidate['provenance']['source_commit']
    capability = q.std.source_capability(commit)
    require(policy['source_commit'] == commit and policy['capability'] == capability,
            'actual remap source/build policy proof required')
    spec['provenance'].update(std_source_paths=capability,
        source_preflight_sha256=preflight_reference['sha256'], source_policy_proof_sha256=policy_reference['sha256'])
    spec['prepublication_qualification'] = dict(policy=q.FINAL)
    q.runtime.identity_for(spec)
    return spec


def installation_commands(q, spec, owner, work, environment):
    runtime = q.runtime
    identity = runtime.identity_for(spec)
    key = runtime.digest(identity)
    sysroot = owner/'.work'/runtime.NAMESPACE/key/'sysroot'
    compiler = runtime.RuntimeCompiler(key, sysroot, identity)
    env = compiler.environment(environment)
    loader = [['/usr/bin/otool', '-l', str(sysroot/name)] for name in sorted(spec['loader'])]
    probes = [[str(compiler.rustc), '-vV'], [str(compiler.rustc), '--print', 'sysroot'],
              [str(compiler.rustc), '-Zhelp']]
    rows = [dict(argv=argv, cwd=str(owner), environment=env, expected=[0],
                 output=str(work/'commands'/f'{index:03}'))
            for index, argv in enumerate(loader+probes)]
    source_work = work/'source-probe'
    rows += [dict(argv=argv, cwd=str(source_work), environment=env, expected=[1],
                  output=str(source_work/'commands'/str(index)))
             for index, argv in enumerate(q.probe_commands(compiler.rustc, sysroot, source_work))]
    return key, sysroot, rows


def execute_installation(q, spec, *, owner, work, environment, preflight_reference,
                         run, simple_run, capacity, full_guard, all_commands_completed):
    full_guard()
    identity = q.runtime.identity_for(spec)
    validator = q.final_validator(owner=owner, work=work/'source-probe',
        expected_identity=identity, preflight_reference=preflight_reference, run=run, guard=capacity)
    def before_publication(compiler, env):
        reference = validator(compiler, env)
        full_guard()
        require(all_commands_completed(), 'final publication before the complete exact probe recipe')
        return reference
    compiler = q.runtime.install_runtime_compiler(owner, spec, run=simple_run, guard=capacity,
        environment=environment, validate_before_publication=before_publication)
    full_guard()
    return compiler

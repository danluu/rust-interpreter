"""First actual source-preflight audit, without requiring its own future audit.

The common reader authenticates the original complete freeze, two saved children,
outer closure and snapshots first. This function reads only through its callbacks;
it does not call q.preflight, run_pair, a compiler or a runtime constructor.
"""
import hashlib
import json
from pathlib import Path
import stat


def require(value, message):
    if not value:
        raise RuntimeError(message)


def same(left, right):
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False)
    return encode(left) == encode(right)


def validate(*, plan, spec, terminal, children, runtime, q, recipe,
             read_json, read_bytes, sha, identity, inventory, guard):
    work = Path(plan['work']); probe = work/'source-probe'; path = probe/'result.json'
    result = read_json(path); expected = runtime.identity_for(spec)
    component = next(row for row in spec['components'] if row['role'] == 'runtime')
    sysroot = Path(component['root']); checkout = Path(expected['provenance']['source_checkout'])
    commit = expected['provenance']['source_commit']
    require(plan['phase'] == terminal['phase'] == 'preflight' and terminal['status'] == 'passed'
            and 'std_source_paths' not in expected['provenance']
            and terminal['runtime_key'] == runtime.digest(expected), 'unqualified exact preflight identity required')
    require(sha(plan['specification']['path']) == plan['specification']['sha256']
            and same(read_json(plan['specification']['path']), spec), 'actual candidate bytes differ')
    require(recipe.POLICY == 'saved-runtime-recipe-v1', 'authenticated independent pure recipe required')
    desired = recipe.preflight_commands(q, spec, Path(plan['owner']), probe, plan['environment'])
    require(len(desired) == len(children) == len(terminal['children']) == 2
            and same(desired, plan['children']) and same([row['declaration'] for row in children], desired),
            'exact two actual preflight children required')
    require(result['status'] == 'passed' and type(result['schema_version']) is int and result['schema_version'] == 1
            and result['policy'] == q.PREFLIGHT and result['full_current_guard_passed'] is True
            and result['candidate_sha256'] == runtime.digest(spec) and result['candidate_is_not_installation'] is True
            and result['capability_added'] is False and result['exact_source_paths_observed'] is True
            and result['full_presentation_qualified'] is False and result['application_qualified'] is False
            and result['std_mir_prepared'] is False and len(result['commands']) == 2,
            'actual preflight result scope differs')
    require(result['owner'] == plan['owner'] and result['work'] == str(probe)
            and result['pid'] == terminal['pid'] and result['parent_pid'] == terminal['parent_pid']
            and result['runtime_sysroot'] == str(sysroot) and result['compiler'] == expected['compiler']
            and result['source_commit'] == commit and result['runtime_rustc_sha256'] == expected['files']['bin/rustc']
            and result['files_sha256'] == runtime.digest(expected['files'])
            and result['source_sha256'] == expected['source_sha256']
            and terminal['admitted_at'] <= result['started_at'] <= result['finished_at'] <= terminal['finished_at']
            and terminal['source_preflight_sha256'] == sha(path), 'actual preflight result association differs')
    files = {name[len(q.std.SOURCE):]: digest for name, digest in expected['files'].items()
             if name.startswith(q.std.SOURCE)}
    source = probe/'source.rs'
    require(read_bytes(source) == q.PROBE, 'actual preflight source differs')
    touched = set()
    def payload(relative):
        guard()
        require(relative in files and runtime.relative(relative) == relative, 'unadmitted diagnostic source')
        original = checkout/'library'/relative; retained = probe/'sources'/relative
        require(same(result['retained_sources'][relative], dict(path=str(retained), sha256=files[relative])),
                'retained source reference differs')
        actual = identity(original); copied = identity(retained)
        require(stat.S_ISREG(copied['mode']) and copied['nlink'] == 1
                and (copied['dev'], copied['ino']) != (actual['dev'], actual['ino']),
                'preflight retained source must be an independent ordinary copy')
        data = read_bytes(original)
        require(hashlib.sha256(data).hexdigest() == files[relative] == sha(original) == sha(retained)
                and data == read_bytes(retained), 'current/retained diagnostic source bytes differ')
        touched.add(relative)
        return data
    observations = []
    for index, (row, proof) in enumerate(zip(children, result['commands'], strict=True)):
        child = row['receipt']; child_path = probe/'commands'/str(index)/'receipt.json'
        require(child['returncode'] == 1 and not row['stdout']
                and same(result['environment'], row['declaration']['environment'])
                and result['started_at'] <= child['started_at'] <= child['finished_at'] <= result['finished_at'],
                'preflight diagnostic process differs')
        diagnostics = [json.loads(line) for line in row['stderr'].splitlines() if line.strip()]
        observed = q.validate_observation(diagnostics, application=source,
            local_roots=(sysroot/'lib/rustlib/src/rust/library', checkout/'library'),
            virtual_root=Path('/rustc')/commit/'library', files=files, payload_for=payload, virtual=index == 1)
        require(same(proof, dict(path=str(child_path), sha256=sha(child_path), observed=observed)),
                'saved preflight diagnostic observations differ')
        observations.append(observed)
    require(set(result['retained_sources']) == touched, 'preflight source retention has missing or extra members')
    guard()
    return dict(direct_children=2, result_sha256=sha(path), source_observations=observations,
        retained_source_paths=sorted(str(probe/'sources'/name) for name in touched),
        reference=dict(path=str(path), sha256=sha(path)), candidate_is_not_installation=True,
        capability_added=False, application_qualified=False, std_mir_prepared=False,
        exporter_qualified=False, performance_measurement=False)

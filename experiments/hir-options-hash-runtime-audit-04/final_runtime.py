"""Read a completed final-root installation; never install, probe or publish.

The enclosing reader authenticates definition modules, the complete compact
input union, current providers, and ordered child/raw/process history. These
predicates use only its scoped read callbacks and pure policy functions. No
RuntimeCompiler constructor, installer, source-validator factory, controller,
or direct filesystem operation is invoked here.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
STAMP_FIELDS = ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def same(left, right):
    return encoded(left) == encoded(right)


def checked_identity(value, kind=None):
    require(type(value) is dict and set(value) == set(FIELDS)
            and all(type(value[key]) is int and value[key] >= 0 for key in FIELDS)
            and value['ino'] > 0 and value['nlink'] > 0, 'invalid actual seven-field identity')
    if kind is not None:
        predicate = {'file': stat.S_ISREG, 'directory': stat.S_ISDIR,
                     'link': stat.S_ISLNK}[kind]
        require(predicate(value['mode']), 'actual entry kind differs')
    return value


def stamp(value):
    return [checked_identity(value)[key] for key in STAMP_FIELDS]


def validate(*, plan, spec, terminal, children, runtime, q, recipe,
             read_json, read_bytes, sha, identity, inventory, guard):
    """Return independently read installation facts, not a new qualification.

``children`` is the enclosing reader's fully authenticated ordered sequence of
declaration/receipt/stdout/stderr records. ``inventory`` rehashes every ordinary
file, includes '.', and checks complete stable membership without following
links. ``identity`` returns named seven-field no-follow metadata. Provider
links/routes are already covered by the enclosing complete frozen-input guard;
this function additionally compares the installer's admission stamps to them.
The ``recipe`` argument is the separately authenticated audit04 pure reader;
no original producer recipe, constructor, or executing function is called.
    """
    guard()
    owner, work = Path(plan['owner']), Path(plan['work'])
    expected_identity = runtime.identity_for(spec)
    key = runtime.digest(expected_identity)
    prefix = owner/'.work'/runtime.NAMESPACE/key
    sysroot = prefix/'sysroot'
    source_work = work/'source-probe'
    require(plan['phase'] == terminal['phase'] == 'installation'
            and terminal['status'] == 'passed'
            and plan['runtime_key'] == terminal['runtime_key'] == terminal['installed_runtime_key'] == key
            and plan['sysroot'] == terminal['sysroot'] == str(sysroot),
            'actual final-root runtime identity differs')
    require(owner.is_absolute() and str(owner) == plan['owner'] and '..' not in owner.parts
            and work.is_relative_to(owner/'.work') and work != owner/'.work', 'runtime owner/work differs')
    for field in ['application_qualified', 'performance_measurement', 'exporter_qualified', 'std_mir_prepared']:
        require(terminal[field] is False, 'unearned runtime qualification scope')
    require(runtime.qualification_policy(spec) == q.FINAL
            and same(expected_identity['provenance']['std_source_paths'],
                     q.std.source_capability(expected_identity['provenance']['source_commit'])),
            'actual final source capability declaration required')
    require(recipe.POLICY == 'saved-runtime-recipe-v1', 'authenticated independent pure recipe required')
    recipe_key, recipe_sysroot, desired = recipe.installation_commands(q, spec, owner, work, plan['environment'])
    count = len(spec['loader']) + 5
    require(len(children) == len(plan['children']) == len(terminal['children']) == count
            and recipe_key == key and recipe_sysroot == sysroot and same(plan['children'], desired)
            and same([row['declaration'] for row in children], plan['children']),
            'complete loader/version/sysroot/options/two-source recipe required')

    before = inventory(prefix)
    ready_path, admission_path, proof_path = [prefix/name for name in
                                            ['ready.json', 'admission.json', 'qualification.json']]
    ready, admission, proof = [read_json(path) for path in [ready_path, admission_path, proof_path]]
    metadata_hashes = {path.name: sha(path) for path in [ready_path, admission_path, proof_path]}
    files, source_paths = {}, {}
    for component in spec['components']:
        for name, row in component['files'].items():
            output = component['destination']+'/'+name if component['destination'] else name
            require(output not in files, 'duplicate installed payload path')
            files[output], source_paths[output] = row, Path(component['root'])/name
    require(same({name: row['sha256'] for name, row in files.items()}, expected_identity['files']),
            'complete admitted payload differs')
    wanted_files = {'sysroot/'+name for name in files} | set(metadata_hashes)
    wanted_dirs = {'.', 'sysroot'}
    for name in wanted_files:
        wanted_dirs.update(str(parent) for parent in PurePosixPath(name).parents)
    require(set(before) == wanted_files | wanted_dirs, 'installed prefix has missing or extra entries')
    for name, row in before.items():
        guard()
        kind = 'file' if name in wanted_files else 'directory'
        require(row['kind'] == kind and set(row) == ({'kind', 'identity', 'sha256'} if kind == 'file'
                                                  else {'kind', 'identity'}), 'installed inventory row differs')
        actual = checked_identity(row['identity'], kind)
        require(not actual['mode'] & 0o222, 'installed entry is writable')
        if kind == 'file':
            require(actual['nlink'] == 1, 'installed file is not an independent ordinary copy')
    require(stat.S_IMODE(before['.']['identity']['mode']) == 0o555, 'published prefix mode differs')
    for name, digest in metadata_hashes.items():
        require(before[name]['sha256'] == digest
                and stat.S_IMODE(before[name]['identity']['mode']) == 0o444,
                'immutable publication record bytes or mode differ')
    ready_stamps = {name.removeprefix('sysroot/'): stamp(row['identity'])[:6]
                   for name, row in before.items() if name.startswith('sysroot/')}
    ready_stamps['.'] = stamp(before['sysroot']['identity'])[:6]
    require(same(ready['identity'], expected_identity) and same(admission['identity'], expected_identity)
            and ready['status'] == 'installed' and ready['application_qualified'] is False
            and ready['owner'] == str(owner) and ready['key'] == key and ready['sysroot'] == str(sysroot)
            and same(ready['stamps'], ready_stamps), 'ready/admission identity or complete stamps differ')

    require(set(admission) == {'identity', 'snapshots'}
            and len(admission['snapshots']) == len(spec['components']), 'complete input admission required')
    for component, snapshot in zip(spec['components'], admission['snapshots'], strict=True):
        require(set(snapshot) == {'files', 'links', 'directories'}
                and set(snapshot['files']) == set(component['files'])
                and set(snapshot['links']) == set(component['links'])
                and '.' in snapshot['directories'], 'admitted source inventory differs')
        for role, kind in [('files', 'file'), ('links', 'link'), ('directories', 'directory')]:
            for name, saved in snapshot[role].items():
                guard()
                require((name == '.' and role == 'directories') or runtime.relative(name) == name,
                        'invalid admitted component entry')
                actual = checked_identity(identity(Path(component['root'])/name), kind)
                require(same(saved, stamp(actual)), 'current admitted component identity differs')
    total_bytes = 0
    for name, row in files.items():
        guard()
        installed = before['sysroot/'+name]
        actual = installed['identity']; source = checked_identity(identity(source_paths[name]), 'file')
        require(installed['sha256'] == row['sha256'] and actual['size'] == row['size']
                and stat.S_IMODE(actual['mode']) == row['mode'] & ~0o222
                and source['size'] == row['size'] and stat.S_IMODE(source['mode']) == row['mode']
                and (actual['dev'], actual['ino']) != (source['dev'], source['ino']),
                'installed payload bytes/mode or independent inode differs')
        total_bytes += actual['size']

    # Common history already binds raw digests, exact argv/env and process times.
    # Re-parse every successful final-root loader/CLI stdout independently.
    loader = {}
    for index, name in enumerate(sorted(spec['loader'])):
        row = children[index]
        require(row['receipt']['returncode'] == 0 and not row['stderr'], 'actual loader probe failed')
        loader[name] = runtime.macho_commands(row['stdout'].decode('utf-8', 'strict'))
    offset = len(loader)
    cli = children[offset:offset+3]
    require(all(row['receipt']['returncode'] == 0 and not row['stderr'] for row in cli),
            'actual final-root compiler CLI probe failed')
    probes = dict(loader=loader, compiler=cli[0]['stdout'].decode('utf-8', 'strict'),
                  sysroot=cli[1]['stdout'].decode('utf-8', 'strict'),
                  options=runtime.option_proof(cli[2]['stdout'].decode('utf-8', 'strict')))
    require(same(probes, ready['probes']) and same(loader, spec['loader'])
            and probes['compiler'] == spec['compiler'] and probes['sysroot'] == str(sysroot)+'\n'
            and same(probes['options'], spec['unstable_options']), 'actual saved loader/CLI proof differs')

    result_path = source_work/'result.json'
    result = read_json(result_path); result_sha = sha(result_path)
    result_identity = checked_identity(identity(result_path), 'file')
    require(result_identity['nlink'] == 1 and same(proof, result)
            and metadata_hashes['qualification.json'] == result_sha
            and (result_identity['dev'], result_identity['ino']) !=
                (before['qualification.json']['identity']['dev'], before['qualification.json']['identity']['ino'])
            and same(ready['prepublication_qualification'], dict(policy=q.FINAL, receipt='qualification.json',
                sha256=result_sha, stamp=stamp(before['qualification.json']['identity']))),
            'retained final source qualification differs')
    commit = expected_identity['provenance']['source_commit']
    require(result['status'] == 'passed' and result['schema_version'] == 1 and type(result['schema_version']) is int
            and result['policy'] == q.FINAL and result['key'] == key and result['owner'] == str(owner)
            and result['work'] == str(source_work) and result['sysroot'] == result['runtime_sysroot'] == str(sysroot)
            and result['compiler'] == expected_identity['compiler'] and result['source_commit'] == commit
            and result['runtime_rustc_sha256'] == expected_identity['files']['bin/rustc']
            and result['files_sha256'] == runtime.digest(expected_identity['files'])
            and result['source_sha256'] == expected_identity['source_sha256']
            and result['pid'] == terminal['pid'] and result['parent_pid'] == terminal['parent_pid']
            and result['exact_source_paths_observed'] is True and result['full_presentation_qualified'] is False
            and result['application_qualified'] is False and result['std_mir_prepared'] is False
            and terminal['admitted_at'] <= result['started_at'] <= result['finished_at'] <= terminal['finished_at']
            and len(result['commands']) == 2, 'actual final source result association differs')
    reference = plan['source_preflight']
    require(set(reference) == {'path', 'sha256'} and same(result['preflight_reference'], reference)
            and expected_identity['provenance']['source_preflight_sha256'] == reference['sha256']
            and sha(reference['path']) == reference['sha256'], 'actual preceding source preflight differs')
    previous = read_json(reference['path'])
    require(previous['status'] == 'passed' and previous['policy'] == q.PREFLIGHT
            and previous['full_current_guard_passed'] is True and previous['exact_source_paths_observed'] is True
            and previous['finished_at'] <= terminal['started_at'] and len(previous['commands']) == 2
            and all(same(previous[field], result[field]) for field in
                ['compiler', 'runtime_rustc_sha256', 'files_sha256', 'source_sha256', 'source_commit'])
            and same(plan['source_preflight_readback']['reference'], reference)
            and same(plan['source_preflight_readback']['result'], previous),
            'full actual preflight readback does not bind final runtime')
    source_files = {name[len(runtime.SOURCE):]: digest for name, digest in expected_identity['files'].items()
                    if name.startswith(runtime.SOURCE)}
    library = sysroot/runtime.SOURCE
    application = source_work/'source.rs'
    require(read_bytes(application) == q.PROBE, 'actual source probe application differs')
    touched = set()
    def payload(relative):
        guard()
        require(relative in source_files and runtime.relative(relative) == relative, 'unadmitted diagnostic source')
        source = library/relative; retained_path = source_work/'sources'/relative
        retained = result['retained_sources'][relative]
        require(same(retained, dict(path=str(retained_path), sha256=source_files[relative])),
                'retained diagnostic source route differs')
        retained_identity = checked_identity(identity(retained_path), 'file')
        installed_identity = before['sysroot/'+runtime.SOURCE+relative]['identity']
        require(retained_identity['nlink'] == 1
                and (retained_identity['dev'], retained_identity['ino']) !=
                    (installed_identity['dev'], installed_identity['ino']), 'retained diagnostic source is aliased')
        data = read_bytes(source); saved = read_bytes(retained_path)
        require(data == saved and hashlib.sha256(data).hexdigest() == source_files[relative]
                and sha(retained_path) == source_files[relative], 'actual/retained diagnostic source bytes differ')
        touched.add(relative)
        return data
    observations = []
    for index, (row, reference) in enumerate(zip(children[-2:], result['commands'], strict=True)):
        receipt = row['receipt']; declaration = row['declaration']
        path = source_work/'commands'/str(index)/'receipt.json'
        require(Path(declaration['output']) == path.parent and reference['path'] == str(path)
                and reference['sha256'] == sha(path) and receipt['returncode'] == 1 and not row['stdout']
                and same(result['environment'], declaration['environment'])
                and result['started_at'] <= receipt['started_at'] <= receipt['finished_at'] <= result['finished_at'],
                'actual final source child association differs')
        diagnostics = [json.loads(line) for line in row['stderr'].splitlines() if line.strip()]
        observed = q.validate_observation(diagnostics, application=application, local_roots=(library,),
            virtual_root=Path('/rustc')/commit/'library', files=source_files, payload_for=payload, virtual=index == 1)
        require(same(reference, dict(path=str(path), sha256=sha(path), observed=observed)),
                'saved final source diagnostic observations differ')
        observations.append(observed)
    require(set(result['retained_sources']) == touched, 'final source retention omits or adds a source')
    guard()
    require(same(inventory(prefix), before), 'installed bytes, modes, membership or identities changed during audit')
    for path in [ready_path, admission_path, proof_path]:
        require(sha(path) == metadata_hashes[path.name], 'installed publication record changed during audit')
    require(sha(result_path) == result_sha, 'external final source result changed during audit')
    return dict(runtime_key=key, sysroot=str(sysroot), direct_children=count,
        ordinary_files_independently_hashed=len(files), runtime_bytes_independently_hashed=total_bytes,
        installed_directories=len(wanted_dirs), ready_sha256=metadata_hashes['ready.json'],
        admission_sha256=metadata_hashes['admission.json'], qualification_sha256=metadata_hashes['qualification.json'],
        result_sha256=result_sha, source_observations=observations, fresh_independent_inodes=True,
        immutable_modes_checked=True, exact_before_after_inventory=True, native_reexecution=False,
        application_qualified=False, std_mir_prepared=False, exporter_qualified=False, performance_measurement=False)

"""Two recorded native source probes and an explicit runtime publication hook.

The enclosing admitted controller owns the canonical lock, complete current
compiler/source guards and owned_stage.run callback. This module creates no
process itself, discovers no input inventory and cannot publish a runtime.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import time

import runtime_compiler as runtime
import std_mir_source_paths as std
from custom_compiler import digest, require, valid_key
from verified_std_diagnostics import source_span_text
from workflow_io import write_json

PREFLIGHT = 'native-runtime-source-preflight-v1'
FINAL = 'native-runtime-installed-source-v1'
PROBE = b'const UNCALLED: u32 = panic!("std source lookup probe");\n'
OPTION = 'translate-remapped-path-to-local-path'
REQUIRED = {'core/src/panic.rs', 'std/src/macros.rs'}


def file_bytes(path, expected, guard):
    """Read the small retained proof/span files, never an unbounded input tree."""
    path = runtime.absolute(str(path))
    require(path.resolve(strict=True) == path and valid_key(expected), 'indirect source/proof file')
    before = runtime.stamp(path.lstat())
    require(stat.S_ISREG(before[2]) and before[3] <= 32 * runtime.BLOCK, 'invalid source/proof size')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        require(runtime.stamp(os.fstat(fd)) == before, 'source/proof changed before read')
        chunks, size = [], 0
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            while chunk := stream.read(runtime.BLOCK):
                guard()
                size += len(chunk)
                require(size <= before[3], 'source/proof grew during read')
                chunks.append(chunk)
        payload = b''.join(chunks)
        require(size == before[3] and hashlib.sha256(payload).hexdigest() == expected
                and runtime.stamp(os.fstat(fd)) == before, 'source/proof bytes changed')
    finally:
        os.close(fd)
    guard()
    require(runtime.stamp(path.lstat()) == before, 'source/proof path changed during read')
    return payload


def spans(value):
    if isinstance(value, list):
        for child in value:
            yield from spans(child)
    elif isinstance(value, dict):
        if 'file_name' in value:
            yield value
        for child in value.values():
            yield from spans(child)


def validate_observation(records, *, application, local_roots, virtual_root,
                         files, payload_for, virtual):
    """Inspect the original records without altering any path or snippet."""
    require(any(d.get('level') == 'error' and (d.get('code') or {}).get('code') == 'E0080'
                for d in records), 'native source probe did not report E0080')
    seen, observations = set(), []
    for span in spans(records):
        name = span['file_name']
        require(isinstance(name, str), 'invalid diagnostic filename')
        path = Path(name)
        require(str(path) == name and '..' not in path.parts, 'noncanonical diagnostic filename')
        if path == application:
            continue
        roots = (virtual_root,) if virtual else local_roots
        matches = [str(path.relative_to(root)) for root in roots
                   if path.is_absolute() and path.is_relative_to(root)]
        require(len(matches) == 1 and matches[0] in files, 'unexpected native standard source: ' + name)
        relative = matches[0]
        payload = payload_for(relative)
        expected = source_span_text(span, payload)
        require(isinstance(span.get('text'), list), 'missing raw source text field')
        if virtual:
            # This second control proves the remapped identity. Some versions
            # may omit a snippet when local display translation is disabled.
            require(span['text'] == [] or span['text'] == expected, 'virtual source snippet differs')
        else:
            require(span['text'] and span['text'] == expected, 'local source snippet missing or different')
        seen.add(relative)
        observations.append(dict(file_name=name, source=relative, sha256=files[relative],
                                 has_text=bool(span['text'])))
    require(REQUIRED <= seen, 'native probe must expose both core and std source expansions')
    return dict(sources=sorted(seen), spans=observations)


def probe_commands(rustc, sysroot, work):
    common = [str(rustc), str(work / 'source.rs'), '--crate-type=lib', '--edition=2024',
              '--emit=metadata', '--error-format=json', '--sysroot', str(sysroot)]
    return [common + ['-o', str(work / 'local.rmeta')],
            common + ['-Z' + OPTION + '=no', '-o', str(work / 'virtual.rmeta')]]


def run_pair(compiler, *, owner, work, environment, local_roots, actual_library,
             files, run, guard, final=False):
    """Use the exact owned_stage.run API for two ordinary rustc invocations."""
    owner, work = runtime.absolute(str(owner)), runtime.absolute(str(work))
    require(work.is_relative_to(owner / '.work') and work != owner / '.work', 'probe work is outside owner')
    require(not work.exists() and not work.is_symlink(), 'native source probe work must be fresh')
    require(owner.resolve(strict=True) == owner, 'indirect source probe owner')
    require(not any(p.is_symlink() for p in work.parents), 'indirect source probe ancestor')
    std.validate_environment(environment)
    checked_environment = compiler.environment(environment)
    if final:
        # The installer already applied its environment method before calling
        # the hook. Validate it without prepending the runtime bin twice.
        env = environment.copy()
        require(env.get('RUSTC') == str(compiler.rustc)
                and env.get('PATH', '').split(os.pathsep)[0] == str(compiler.sysroot / 'bin'),
                'final hook did not receive the installed compiler environment')
    else:
        env = checked_environment
    compiler.require_option(OPTION)
    guard()
    work.mkdir(parents=True)
    require(work.resolve(strict=True) == work, 'indirect source probe directory')
    source = work / 'source.rs'
    with source.open('xb') as output:
        output.write(PROBE)
    record = dict(schema_version=1, status='running', owner=str(owner), work=str(work),
                  pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
                  runtime_sysroot=str(compiler.sysroot), compiler=compiler.identity['compiler'],
                  source_commit=compiler.identity['provenance']['source_commit'],
                  runtime_rustc_sha256=compiler.identity['files']['bin/rustc'],
                  files_sha256=digest(compiler.identity['files']),
                  source_sha256=compiler.identity['source_sha256'], environment=env,
                  commands=[], application_qualified=False, std_mir_prepared=False)
    write_json(work / 'result.json', record)
    retained = {}
    def payload_for(relative):
        require(relative in files and runtime.relative(relative) == relative, 'unknown source reference')
        payload = file_bytes(actual_library / relative, files[relative], guard)
        destination = work / 'sources' / relative
        if relative not in retained:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as output:
                output.write(payload)
            require(destination.lstat().st_nlink == 1, 'retained source is not a fresh copy')
            retained[relative] = dict(path=str(destination), sha256=files[relative])
        require(file_bytes(destination, files[relative], guard) == payload, 'retained source readback differs')
        return payload
    try:
        commands = probe_commands(compiler.rustc, compiler.sysroot, work)
        for index, argv in enumerate(commands):
            guard()
            out = work / 'commands' / str(index)
            try:
                child = run(argv, cwd=work, env=env.copy(), out=out, capacity_root=owner, expected=(1,))
            finally:
                if (out / 'receipt.json').exists():
                    receipt = (out / 'receipt.json').read_bytes()
                    record['commands'].append(dict(path=str(out / 'receipt.json'),
                        sha256=hashlib.sha256(receipt).hexdigest()))
                    write_json(work / 'result.json', record)
            guard()
            require(child['status'] == 'finished' and child['returncode'] == 1
                    and child['command'] == argv and child['cwd'] == str(work)
                    and child['environment'] == env and child['supervisor_pid'] == os.getpid()
                    and child['parent_pid'] == os.getppid()
                    and record['started_at'] <= child['started_at'] <= child['finished_at'],
                    'native probe command/process association differs')
            require(not file_bytes(out / 'stdout', child['stdout_sha256'], guard), 'unexpected native probe stdout')
            stderr = file_bytes(out / 'stderr', child['stderr_sha256'], guard)
            diagnostics = [json.loads(line) for line in stderr.splitlines() if line.strip()]
            if final and index == 0:
                # This is the existing v2 predicate, with the actual ordinary R
                # root; no source-link exception is added to production code.
                std.validate_probe(diagnostics, actual_library, files)
            observed = validate_observation(diagnostics, application=source, local_roots=local_roots,
                virtual_root=Path('/rustc') / record['source_commit'] / 'library', files=files,
                payload_for=payload_for, virtual=index == 1)
            record['commands'][-1]['observed'] = observed
            require(source.read_bytes() == PROBE, 'native probe source changed')
            write_json(work / 'result.json', record)
        guard()
        record.update(status='passed', finished_at=time.time(), retained_sources=retained,
                      exact_source_paths_observed=True, full_presentation_qualified=False)
        write_json(work / 'result.json', record)
        return record
    except BaseException as error:
        record.update(status='failed', finished_at=time.time(), error=repr(error))
        write_json(work / 'result.json', record)
        raise


def preflight(candidate, *, owner, work, environment, run, guard):
    """Observe existing E; do not infer capability or change the candidate."""
    candidate = copy.deepcopy(candidate)
    identity = runtime.identity_for(candidate)
    require('std_source_paths' not in identity['provenance'], 'preflight expects unqualified candidate')
    component = next(c for c in candidate['components'] if c['role'] == 'runtime')
    sysroot = Path(component['root'])
    checkout = Path(identity['provenance']['source_checkout'])
    link = sysroot / 'lib/rustlib/src/rust'
    declaration = component['links'].get('lib/rustlib/src/rust')
    require(declaration and declaration['action'] == 'replace'
            and link.is_symlink() and os.readlink(link) == declaration['text']
            and link.resolve(strict=True) == checkout, 'E source link differs from admitted mapping')
    before = runtime.stamp(link.lstat())
    compiler = runtime.RuntimeCompiler(digest(identity), sysroot, identity)
    files = {p[len(std.SOURCE):]: h for p, h in identity['files'].items() if p.startswith(std.SOURCE)}
    def current_guard():
        guard()
        require(runtime.stamp(link.lstat()) == before and os.readlink(link) == declaration['text']
                and link.resolve(strict=True) == checkout, 'E source link changed during probe')
    result = run_pair(compiler, owner=owner, work=work, environment=environment,
        local_roots=(link / 'library', checkout / 'library'), actual_library=checkout / 'library',
        files=files, run=run, guard=current_guard)
    result.update(policy=PREFLIGHT, candidate_sha256=digest(candidate),
                  candidate_is_not_installation=True, capability_added=False)
    write_json(Path(work) / 'result.json', result)
    return result


def final_validator(*, owner, work, expected_identity, preflight_reference, run, guard):
    """Bind the reviewed predecessor and return the installer's explicit hook.

    A separate reviewed specification must already contain std_source_paths,
    source_preflight_sha256 and this FINAL declaration. This factory never adds
    capabilities to either the original candidate or an existing installation.
    """
    expected_identity = copy.deepcopy(expected_identity)
    expected_key = digest(expected_identity)
    def validate(compiler, environment):
        require(compiler.key == expected_key and compiler.identity == expected_identity
                and compiler.sysroot == Path(owner) / '.work' / runtime.NAMESPACE / expected_key / 'sysroot',
                'final source validator received another runtime')
        require(runtime.qualification_policy(compiler.identity['admission']) == FINAL,
                'final source policy declaration differs')
        require(compiler.identity['provenance'].get('source_preflight_sha256') == preflight_reference['sha256'],
                'final runtime does not bind reviewed E source preflight')
        previous = json.loads(file_bytes(preflight_reference['path'], preflight_reference['sha256'], guard))
        require(previous['status'] == 'passed' and previous['policy'] == PREFLIGHT
                and previous.get('full_current_guard_passed') is True
                and previous['compiler'] == compiler.identity['compiler']
                and previous['runtime_rustc_sha256'] == compiler.identity['files']['bin/rustc']
                and previous['files_sha256'] == digest(compiler.identity['files'])
                and previous['source_sha256'] == compiler.identity['source_sha256']
                and previous['source_commit'] == compiler.identity['provenance']['source_commit']
                and previous['exact_source_paths_observed'] and len(previous['commands']) == 2,
                'reviewed E source preflight does not match final runtime')
        _, files = std.compiler_sources(compiler)
        library = compiler.sysroot / std.SOURCE
        result = run_pair(compiler, owner=owner, work=work, environment=environment,
            local_roots=(library,), actual_library=library, files=files, run=run, guard=guard, final=True)
        result.update(policy=FINAL, key=compiler.key, sysroot=str(compiler.sysroot),
                      preflight_reference=preflight_reference)
        path = Path(work) / 'result.json'
        write_json(path, result)
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return validate

"""A separate immutable native-runtime policy; never a complete stage2 install.

The caller supplies an admitted inventory and supervised probe/capacity callbacks.
No discovery, download, application qualification, or tool publication is implicit.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

from custom_compiler import Compiler, digest, read_json, require, tree_stamps, valid_key
from workflow_io import write_json

POLICY = 'owned-native-runtime-compiler-v1'
NAMESPACE = 'runtime-compilers'
LOADER_POLICY = 'darwin-relative-runtime-closure-v1'
SOURCE = 'lib/rustlib/src/rust/library/'
SOURCE_ROOTS = ('lib/rustlib/src/rust', 'lib/rustlib/rustc-src/rust')
CRATES = ('core', 'alloc', 'std', 'test', 'proc_macro')
REQUIRED_SOURCES = ('Cargo.toml', 'Cargo.lock', 'core/src/lib.rs', 'alloc/src/lib.rs',
                    'std/src/lib.rs', 'test/src/lib.rs', 'proc_macro/src/lib.rs')
LOAD_KINDS = {'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
              'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB', 'LC_LOAD_DYLINKER'}
OVERRIDES = ('RUST_SYSROOT', 'RUSTC_FORCE_RUSTC_VERSION',
             'RUSTC_OVERRIDE_VERSION_STRING', 'FORCE_RUSTC_VERSION')
BLOCK = 1024 * 1024


def relative(name):
    require(isinstance(name, str) and name and '\\' not in name and '\x00' not in name
            and not PurePosixPath(name).is_absolute()
            and all(p not in ('', '.', '..') for p in name.split('/')),
            'invalid relative runtime path: ' + repr(name))
    return name


def absolute(name):
    require(isinstance(name, str) and Path(name).is_absolute()
            and str(Path(name)) == name and '..' not in Path(name).parts,
            'invalid absolute runtime input path')
    return Path(name)


def under(name, prefix):
    return name == prefix or name.startswith(prefix + '/')


def option_proof(output):
    return dict(probe='-Zhelp', output=output,
                sha256=hashlib.sha256(output.encode()).hexdigest(),
                supported=sorted(set(re.findall(
                    r'(?m)^\s*(?:-Z\s+)?([a-z][a-z0-9-]*)\s*=', output))))


def require_runtime(records, host):
    require(re.fullmatch(r'[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)+', host) is not None
            and host.endswith('-apple-darwin'), 'runtime policy currently supports Darwin hosts')
    require('bin/rustc' in records and records['bin/rustc']['mode'] & 0o111,
            'runtime is missing executable bin/rustc')
    require('bin/rustdoc' not in records or records['bin/rustdoc']['mode'] & 0o111,
            'supplied runtime rustdoc is not executable')
    require('bin/cargo' not in records, 'runtime must not shadow separately selected Cargo')
    prefix = 'lib/rustlib/' + host + '/lib/'
    for crate in CRATES:
        matches = [p for p in records if p.startswith(prefix + 'lib' + crate + '-')
                   and '/' not in p[len(prefix):] and p.endswith('.rlib')]
        require(len(matches) == 1, 'missing or ambiguous native ' + crate)
        stem = matches[0].removesuffix('.rlib')
        require(all(p.rsplit('.', 1)[0] == stem for p in records
                    if p.startswith(prefix + 'lib' + crate + '-') and '/' not in p[len(prefix):]
                    and p.endswith(('.rmeta', '.dylib'))), 'native metadata/library stem differs: ' + crate)
    drivers = [p for p in records if p.startswith('lib/librustc_driver-')
               and '/' not in p[4:] and p.endswith('.dylib')]
    require(len(drivers) == 1, 'missing or ambiguous runtime driver')
    for name in REQUIRED_SOURCES:
        require(SOURCE + name in records, 'missing ordinary standard source: ' + name)
    # Private rustc-dev metadata and rust-objcopy are not asserted by this policy.
    # Any supplied auxiliary executables are inventoried and loader-checked.


def identity_for(spec):
    """Validate a closed admitted specification without accessing its input paths."""
    require(spec.get('schema_version') == 1 and spec.get('loader_policy') == LOADER_POLICY,
            'unknown runtime specification or loader policy')
    provenance = spec['provenance']
    require(re.fullmatch('[0-9a-f]{40}', provenance.get('source_commit', '')) is not None,
            'missing actual runtime source commit')
    require('stage' not in provenance, 'runtime-only provenance must not claim a bootstrap stage')
    absolute(provenance['source_checkout'])
    for name in ('build_receipt_sha256', 'qualification_receipt_sha256', 'bootstrap_sha256'):
        require(valid_key(provenance.get(name)), 'missing admitted provenance: ' + name)
    version = spec['compiler']
    require(isinstance(version, str) and version.startswith('rustc ')
            and [s[13:] for s in version.splitlines() if s.startswith('commit-hash: ')]
                == [provenance['source_commit']]
            and [s[6:] for s in version.splitlines() if s.startswith('host: ')] == [spec['host']],
            'admitted compiler version, host or source differs')
    require(spec['unstable_options'] == option_proof(spec['unstable_options']['output']),
            'invalid admitted option probe')
    records, native_records, destinations, runtime = {}, {}, [], []
    for component in spec['components']:
        require(component['role'] in ('runtime', 'source', 'support'), 'unknown component role')
        absolute(component['root'])
        destination = component['destination']
        if component['role'] == 'runtime':
            require(destination == '', 'runtime component must be rooted at the sysroot')
            runtime.append(component)
        else:
            relative(destination)
            require(not component['links'], 'only the runtime may contain declared source links')
        if component['role'] == 'source':
            require(any(under(destination, p) for p in SOURCE_ROOTS), 'source provider has a non-source destination')
            require(valid_key(component.get('source_receipt_sha256')), 'source provider lacks admitted proof')
        destinations.append(destination)
        require(component['files'], 'empty runtime component')
        for name, row in component['files'].items():
            relative(name)
            require(set(row) == {'sha256', 'size', 'mode'} and valid_key(row['sha256'])
                    and type(row['size']) is int and row['size'] >= 0
                    and type(row['mode']) is int and 0 <= row['mode'] <= 0o777, 'invalid admitted file record')
            output = destination + '/' + name if destination else name
            if component['role'] != 'source':
                require(not any(under(output, p) for p in SOURCE_ROOTS),
                        'source files require an explicit source provider')
            require(output not in records, 'component file collision: ' + output)
            records[output] = row
            if component['role'] != 'source':
                native_records[output] = row
    require(len(runtime) == 1, 'require exactly one complete admitted runtime component')
    for name in records:
        require(not any(str(p) in records for p in PurePosixPath(name).parents if str(p) != '.'),
                'file/directory collision: ' + name)
    for name, link in runtime[0]['links'].items():
        require(name in SOURCE_ROOTS, 'undeclared source-link kind')
        require(set(link) == {'text', 'resolved_target', 'action', 'reason'}
                and isinstance(link['text'], str) and link['text']
                and link['resolved_target'] == provenance['source_checkout']
                and link['action'] in ('replace', 'omit') and isinstance(link['reason'], str)
                and link['reason'].strip(), 'invalid source-link declaration')
        replaced = any(d and under(d, name) for d in destinations)
        require(replaced == (link['action'] == 'replace'), 'source-link action and provider differ')
        if link['action'] == 'omit':
            require(not any(under(p, name) for p in records), 'omitted source link has installed contents')
    require_runtime(records, spec['host'])
    validate_loader(spec['loader'], native_records)
    files = {p: row['sha256'] for p, row in records.items()}
    return dict(policy=POLICY, host=spec['host'], compiler=version, provenance=provenance,
                admission=spec, files=files, unstable_options=spec['unstable_options'],
                source_sha256=digest({p: h for p, h in files.items() if p.startswith(SOURCE)}))


def macho_commands(output):
    blocks = re.split(r'(?m)^Load command \d+\s*$', output)[1:]
    require(blocks, 'no Mach-O load commands')
    result = dict(rpaths=[], loads=[])
    for block in blocks:
        match = re.search(r'(?m)^\s*cmd (LC_\w+)\s*$', block)
        require(match is not None, 'malformed Mach-O command')
        kind = match[1]
        require(kind != 'LC_DYLD_ENVIRONMENT', 'embedded loader environment is unsupported')
        if kind == 'LC_ID_DYLIB':
            continue  # Library self identity is not a load edge.
        require(not kind.endswith('_DYLIB') or kind in LOAD_KINDS, 'unknown Mach-O load kind')
        if kind == 'LC_RPATH':
            match = re.search(r'(?m)^\s*path (.+) \(offset \d+\)\s*$', block)
            require(match is not None, 'malformed Mach-O rpath')
            result['rpaths'].append(match[1])
        elif kind in LOAD_KINDS:
            match = re.search(r'(?m)^\s*name (.+) \(offset \d+\)\s*$', block)
            require(match is not None, 'malformed Mach-O dependency')
            result['loads'].append([kind, match[1]])
    return result


def validate_loader(loader, records):
    """Check the declared relative closure, including support-tool entry points.

    This deliberately rejects ambiguous rpath resolutions. Actual dyld traces and
    native application behavior remain separate installation qualification gates.
    """
    libraries = {p for p in records if p.endswith(('.dylib', '.so'))}
    programs = {p for p, r in records.items() if r['mode'] & 0o111 and p not in libraries}
    require(set(loader) == libraries | programs, 'loader inventory omits or adds a native image')
    require('bin/rustc' in programs, 'loader inventory lacks rustc entry point')
    for row in loader.values():
        require(set(row) == {'rpaths', 'loads'} and isinstance(row['rpaths'], list)
                and isinstance(row['loads'], list), 'invalid loader declaration')
        require(all(isinstance(p, str) for p in row['rpaths'])
                and all(isinstance(p, list) and len(p) == 2 and p[0] in LOAD_KINDS
                        and isinstance(p[1], str) for p in row['loads']), 'invalid loader edge')

    def local(value, image, executable):
        for prefix, base in (('@loader_path/', PurePosixPath(image).parent),
                             ('@executable_path/', PurePosixPath(executable).parent)):
            if value.startswith(prefix):
                require(not value[len(prefix):].startswith('/') and '\\' not in value
                        and '\x00' not in value, 'invalid relative loader path')
                parts = []
                for part in (base / value[len(prefix):]).parts:
                    if part == '..':
                        require(parts, 'loader path escapes installation')
                        parts.pop()
                    elif part != '.':
                        parts.append(part)
                return str(PurePosixPath(*parts))
        raise RuntimeError('nonrelative runtime loader path: ' + value)

    visited = set()
    def visit(image, executable, inherited, active):
        if image in active:
            return
        search = [local(p, image, executable) for p in loader[image]['rpaths']] + inherited
        for kind, dependency in loader[image]['loads']:
            if kind == 'LC_LOAD_DYLINKER':
                require(dependency == '/usr/lib/dyld', 'non-system runtime dynamic linker')
            if dependency.startswith(('/usr/lib/', '/System/Library/')):
                require('..' not in PurePosixPath(dependency).parts, 'invalid system load path')
                continue
            if dependency.startswith('@rpath/'):
                suffix = relative(dependency[len('@rpath/'):])
                candidates = {str(PurePosixPath(p) / suffix) for p in search
                              if str(PurePosixPath(p) / suffix) in libraries}
                require(len(candidates) == 1, 'missing or ambiguous runtime rpath dependency: ' + dependency)
                target = candidates.pop()
            else:
                target = local(dependency, image, executable)
                require(target in libraries, 'runtime dependency is absent: ' + dependency)
            visit(target, executable, search, active | {image})
        visited.add(image)
    for executable in sorted(programs):
        visit(executable, executable, [], set())
    # Check declared libraries not reached by -vV too (native std/codegen, etc.).
    inherited = [local(p, 'bin/rustc', 'bin/rustc') for p in loader['bin/rustc']['rpaths']]
    for image in sorted(libraries - visited):
        visit(image, 'bin/rustc', inherited, set())


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]


def inspect_component(component):
    root = absolute(component['root'])
    require(root.resolve(strict=True) == root and root.is_dir(), 'component root must be ordinary')
    found, links, directories = {}, {}, {'.': stamp(root.lstat())}
    pending = [(root, '')]
    while pending:
        parent, prefix = pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                name = prefix + entry.name
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories[name] = stamp(info)
                    pending.append((Path(entry.path), name + '/'))
                elif stat.S_ISREG(info.st_mode):
                    found[name] = stamp(info)
                else:
                    require(stat.S_ISLNK(info.st_mode) and name in component['links'],
                            'unexpected component entry: ' + name)
                    declaration = component['links'][name]
                    require(os.readlink(entry.path) == declaration['text']
                            and str(Path(entry.path).resolve(strict=True)) == declaration['resolved_target'],
                            'source-link identity differs: ' + name)
                    links[name] = stamp(info)
    require(set(found) == set(component['files']) and set(links) == set(component['links']),
            'component file/link inventory differs')
    for name, value in directories.items():
        require(stamp((root / name).lstat()) == value, 'component directory changed')
    for name, value in found.items():
        row = component['files'][name]
        require(value[3] == row['size'] and stat.S_IMODE(value[2]) == row['mode'],
                'component file size or executable mode differs: ' + name)
    return dict(files=found, links=links, directories=directories)


def transfer(path, row, expected_stamp, guard, destination=None):
    guard()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    output = None
    try:
        require(stamp(os.fstat(fd)) == expected_stamp, 'source file changed before opening')
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            output = destination.open('xb')
        size, sha = 0, hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as source:
            while block := source.read(BLOCK):
                guard()
                size += len(block)
                sha.update(block)
                if output is not None:
                    output.write(block)
                guard()
        require(stamp(os.fstat(fd)) == expected_stamp, 'source file changed while reading')
        require(size == row['size'] and sha.hexdigest() == row['sha256'], 'source file digest differs')
    finally:
        if output is not None:
            output.close()
        os.close(fd)
    if destination is not None:
        require(destination.stat().st_nlink == 1, 'runtime copy is not a fresh inode')
        destination.chmod(row['mode'])
    guard()


@dataclass(frozen=True)
class RuntimeCompiler(Compiler):
    def require_option(self, option):
        # Runtime options are actual final-root probes, not inferred features.
        proof = self.identity['unstable_options']
        require(proof == option_proof(proof['output']) and option in proof['supported'],
                'runtime has no recorded -Zhelp support for ' + option)

    def environment(self, environment):
        require(not any(k in environment for k in OVERRIDES), 'runtime compiler override is present')
        env = super().environment(environment)
        if 'bin/rustdoc' in self.identity['files']:
            rustdoc = self.sysroot / 'bin/rustdoc'
            require('RUSTDOC' not in env or Path(env['RUSTDOC']).resolve() == rustdoc,
                    'runtime compiler conflicts with RUSTDOC')
            env['RUSTDOC'] = str(rustdoc)
        else:
            require('RUSTDOC' not in env, 'runtime does not provide the requested rustdoc')
        return env

    def revalidate(self, root):
        require(load_runtime_compiler(root, self.key) == self, 'runtime compiler changed')
        return self


def load_runtime_compiler(root, key):
    require(valid_key(key), 'invalid runtime key')
    root = Path(root)
    directory = root / '.work' / NAMESPACE / key
    require(directory.resolve(strict=True) == directory, 'runtime installation root is indirect')
    require(not (directory / 'failure.json').exists(), 'runtime installation previously failed')
    ready_path = directory / 'ready.json'
    require(ready_path.lstat().st_nlink == 1 and not ready_path.lstat().st_mode & 0o222
            and not directory.stat().st_mode & 0o222, 'runtime ready record or directory is writable')
    ready = read_json(ready_path)
    identity = ready['identity']
    require(identity == identity_for(identity['admission']) and digest(identity) == key
            and identity['policy'] == POLICY and ready['owner'] == str(root) and ready['key'] == key,
            'runtime ownership or identity differs')
    sysroot = directory / 'sysroot'
    require(ready['sysroot'] == str(sysroot) and ready['status'] == 'installed'
            and ready['application_qualified'] is False, 'runtime location or qualification differs')
    current = tree_stamps(sysroot)
    require(current == ready['stamps'] and all(not v[2] & 0o222 for v in current.values()),
            'runtime installation changed or is writable')
    require({p for p, s in current.items() if stat.S_ISREG(s[2])} == set(identity['files']),
            'runtime installed file inventory differs')
    for component in identity['admission']['components']:
        for name, row in component['files'].items():
            name = component['destination'] + '/' + name if component['destination'] else name
            require(stat.S_IMODE(current[name][2]) == row['mode'] & ~0o222, 'runtime executable mode differs')
    probes = ready['probes']
    require(probes['compiler'] == identity['compiler'] and probes['sysroot'] == str(sysroot) + '\n'
            and probes['loader'] == identity['admission']['loader']
            and probes['options'] == identity['unstable_options'], 'runtime probe proof differs')
    return RuntimeCompiler(key, sysroot, identity)


def install_runtime_compiler(root, specification, *, run, guard, environment):
    """Install admitted bytes at their FINAL root, then probe and make immutable.

    Caller holds the canonical lock and records every run(argv, env) ->
    {returncode, stdout, stderr}. guard() is mandatory before/after every MiB.
    Failure retains the fresh partial installation; there is no retry or cleanup.
    """
    require(callable(run) and callable(guard), 'supervised run and capacity guard are required')
    require(sys.platform == 'darwin', 'actual runtime installation requires Darwin')
    root = Path(root)
    require(root.resolve(strict=True) == root and root.is_dir(), 'runtime owner must be ordinary')
    spec = json.loads(json.dumps(specification))  # Caller mutation cannot change the admitted plan.
    identity = identity_for(spec)
    key = digest(identity)
    directory = root / '.work' / NAMESPACE / key
    require(not directory.exists() and not directory.is_symlink(), 'runtime installation already exists')
    sysroot = directory / 'sysroot'
    compiler = RuntimeCompiler(key, sysroot, identity)
    env = compiler.environment(environment)
    snapshots = []
    for component in spec['components']:
        snapshot = inspect_component(component)
        for name, row in component['files'].items():
            transfer(Path(component['root']) / name, row, snapshot['files'][name], guard)
        require(inspect_component(component) == snapshot, 'runtime input changed during admission')
        snapshots.append(snapshot)
    guard()
    for parent in (root / '.work', directory.parent):
        if not parent.exists() and not parent.is_symlink():
            parent.mkdir()
        require(parent.resolve(strict=True) == parent and parent.is_dir(), 'runtime namespace is indirect')
    directory.mkdir()
    sysroot.mkdir()
    # The exact final pathname is used for ALL compiler and loader probes.
    write_json(directory / 'admission.json', dict(identity=identity, snapshots=snapshots))
    try:
        for component, snapshot in zip(spec['components'], snapshots):
            for name, row in component['files'].items():
                output = sysroot / component['destination'] / name
                transfer(Path(component['root']) / name, row, snapshot['files'][name], guard, output)
        def check_inputs():
            for component, snapshot in zip(spec['components'], snapshots):
                require(inspect_component(component) == snapshot, 'runtime source inputs changed')
        check_inputs()
        copied = tree_stamps(sysroot)
        require({p for p, s in copied.items() if stat.S_ISREG(s[2])} == set(identity['files']),
                'runtime output inventory differs')
        def probe(argv):
            guard()
            row = run(argv, env.copy())
            require(row['returncode'] == 0 and isinstance(row['stdout'], str)
                    and isinstance(row['stderr'], str), 'runtime probe failed')
            guard()
            return row['stdout']
        loader = {name: macho_commands(probe(['/usr/bin/otool', '-l', str(sysroot / name)]))
                  for name in sorted(spec['loader'])}
        require(loader == spec['loader'], 'actual runtime loader declaration differs')
        probes = dict(loader=loader, compiler=probe([str(compiler.rustc), '-vV']),
                      sysroot=probe([str(compiler.rustc), '--print', 'sysroot']),
                      options=option_proof(probe([str(compiler.rustc), '-Zhelp'])))
        require(probes['compiler'] == spec['compiler'] and probes['sysroot'] == str(sysroot) + '\n',
                'final-root compiler version or sysroot differs')
        require(probes['options'] == spec['unstable_options'], 'final-root option probe differs')
        check_inputs()
        require(tree_stamps(sysroot) == copied, 'runtime files changed during probes')
        for name, value in copied.items():
            (sysroot / name).chmod(stat.S_IMODE(value[2]) & ~0o222)
        ready = dict(status='installed', application_qualified=False, owner=str(root), key=key,
                     sysroot=str(sysroot), identity=identity, stamps=tree_stamps(sysroot), probes=probes)
        write_json(directory / 'ready.json', ready)
        for name in ('admission.json', 'ready.json'):
            (directory / name).chmod(0o444)
        guard()
        directory.chmod(0o555)
        return load_runtime_compiler(root, key)
    except Exception as error:
        # An incomplete installation never acquires a ready record on a failed probe.
        # Preserve partial bytes and caller receipts; do not remove or relabel them.
        if os.access(directory, os.W_OK):
            write_json(directory / 'failure.json', dict(error=str(error), key=key))
        raise

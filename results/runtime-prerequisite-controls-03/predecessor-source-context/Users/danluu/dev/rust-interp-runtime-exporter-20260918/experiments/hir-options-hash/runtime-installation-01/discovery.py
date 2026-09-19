"""Bounded, read-only candidate derivation from actual qualified inputs.

Callbacks read_json/read_bytes/sha must admit each file into the enclosing exact
freeze. Nothing is written or launched here. No future key or proof is supplied.
"""
import copy
import hashlib
from pathlib import Path
import shlex
import stat
import struct
import tomllib


def require(value, message):
    if not value:
        raise RuntimeError(message)


def macho(raw):
    """Planning declaration; unchanged production final-path otool must agree."""
    require(32 <= len(raw) <= 1024*2**20, 'bounded native image required')
    offset = 0
    if raw[:4] in [b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf']:
        count = struct.unpack_from('>I', raw, 4)[0]
        width = 32 if raw[3] == 0xbf else 20
        require(0 < count < 32 and 8+count*width <= len(raw), 'invalid fat image')
        slices = []
        table_end = 8+count*width
        for index in range(count):
            base = 8+index*width
            start, length = struct.unpack_from('>QQ' if width == 32 else '>II', raw, base+8)
            alignment = struct.unpack_from('>I', raw, base+(24 if width == 32 else 16))[0]
            require(start >= table_end and length >= 32 and start+length <= len(raw)
                    and alignment <= 31 and start % (1 << alignment) == 0, 'invalid fat slice range/alignment')
            if width == 32:
                require(struct.unpack_from('>I', raw, base+28)[0] == 0, 'fat64 reserved field differs')
            if struct.unpack_from('>I', raw, base)[0] == 0x100000c:
                slices.append((start, length))
        require(len(slices) == 1, 'one arm64 slice required')
        start, length = slices[0]
        raw = raw[start:start+length]
    require(offset+32 <= len(raw) and raw[offset:offset+4] == b'\xcf\xfa\xed\xfe'
            and struct.unpack_from('<I', raw, offset+4)[0] == 0x100000c, 'arm64 Mach-O required')
    count, size = struct.unpack_from('<II', raw, offset+16)
    position, end = offset+32, offset+32+size
    require(0 < count < 4096 and end <= len(raw), 'bounded load-command table required')
    kinds = {0xc:'LC_LOAD_DYLIB', 0x80000018:'LC_LOAD_WEAK_DYLIB', 0x8000001f:'LC_REEXPORT_DYLIB',
             0x20:'LC_LAZY_LOAD_DYLIB', 0x80000023:'LC_LOAD_UPWARD_DYLIB', 0xe:'LC_LOAD_DYLINKER'}
    result = dict(rpaths=[], loads=[])
    for _ in range(count):
        require(position+8 <= end, 'truncated load command')
        kind, width = struct.unpack_from('<II', raw, position)
        require(width >= 8 and position+width <= end and kind != 0x27, 'invalid/embedded-environment load command')
        if kind in kinds or kind in [0xd, 0x8000001c]:
            require(width >= 12, 'truncated loader string')
            start = struct.unpack_from('<I', raw, position+8)[0]
            require(12 <= start < width, 'invalid loader string offset')
            value = raw[position+start:position+width]
            require(b'\0' in value, 'unterminated loader string')
            token = value.split(b'\0', 1)[0].decode()
            require(bool(token), 'empty loader string')
            if kind == 0x8000001c:
                result['rpaths'].append(token)
            elif kind != 0xd:  # Self identity is not a load edge.
                result['loads'].append([kinds[kind], token])
        position += width
    require(position == end, 'load command count/size differ')
    return result


def source_policy(q, compiled, proof, old_policy, *, read_json, read_bytes, sha, source):
    revision = compiled['candidate_revision']
    require(proof['status'] == 'verified-read-only-derivation' and proof['candidate_revision'] == revision
            and proof['logical_command'] == 16 and proof['actual_native_build'] == compiled['command_history'][16],
            'actual native remap command association differs')
    require(sha(proof['compiled']['path']) == proof['compiled']['sha256']
            and read_json(proof['compiled']['path']) == compiled, 'remap compiled-catalog association differs')
    native_path = Path(compiled['command_history'][16]['path'])
    native = read_json(native_path)
    require(sha(native_path) == compiled['command_history'][16]['sha256']
            and native['status'] == 'finished' and native['returncode'] == 0
            and native['command'] == compiled['command_history'][16]['command'], 'actual native producer differs')
    for stream in ['stdout', 'stderr']:
        raw_ref = proof['raw'][stream]
        require(Path(raw_ref['path']) == native_path.parent/stream
                and sha(raw_ref['path']) == raw_ref['sha256'] == native[stream+'_sha256'],
                'actual native remap raw association differs')
    for path, row in proof['pinned_source_proofs'].items():
        require(sha(path) == row['sha256'], 'remap source proof changed')
    bootstrap = source/'bootstrap.toml'
    require(tomllib.loads(read_bytes(bootstrap).decode())['rust']['remap-debuginfo'] is True,
            'candidate bootstrap remapping disabled')
    reviewed = old_policy['cargo_policy_review']
    require(sha(reviewed['path']) == reviewed['sha256'], 'retained source-path recipe review changed')
    cargo_policy = read_json(reviewed['path'])
    require(cargo_policy['cargo_gitlink_commit'] == q.std.CARGO_COMMIT
            and cargo_policy['cargo_files'] == old_policy['cargo_recipe_files'], 'reviewed Cargo policy pin differs')
    unchanged = {}
    for name, row in old_policy['unchanged_remap_sources'].items():
        require(sha(source/name) == row['sha256'] == cargo_policy['rust_files'][name],
                'candidate remap implementation differs from existing qualified source policy')
        unchanged[name] = dict(path=str(source/name), sha256=row['sha256'])
    observed = set()
    for row in proof['selected_expanded_commands']:
        require(row['stream'] == proof['raw']['stderr']['path'], 'remap row names a foreign stream')
        raw = read_bytes(row['stream']).splitlines()[row['line']-1]
        require(hashlib.sha256(raw).hexdigest() == row['line_sha256'], 'expanded remap raw line differs')
        # Cargo's exact Running line uses backticks around the shell command.
        text = raw.decode().strip()
        require(text.startswith('Running `') and text.endswith('`'), 'expanded compiler line grammar differs')
        argv = shlex.split(text[len('Running `'):-1])
        require([token for token in argv if token.startswith(('--remap-path-prefix=', '--remap-path-scope='))]
                    == row['remap_arguments'] and '--remap-path-scope=all' in argv,
                'actual compiler remap argument sequence differs')
        crate_names = [argv[index+1] for index, token in enumerate(argv[:-1]) if token == '--crate-name']
        require(crate_names == [row['crate']], 'actual expanded crate role differs')
        crate = row['crate']; role = 'rustc' if crate in {'core', 'alloc', 'std'} else 'rustc-dev'
        require('--remap-path-prefix='+str(source)+'=/'+role+'/'+revision in argv, 'candidate source root differs')
        observed.add(crate)
    require({'core', 'alloc', 'std', 'rustc_ast_lowering', 'rustc_interface'} <= observed,
            'actual compiler and std remap roles required')
    return dict(source_commit=revision, capability=q.std.source_capability(revision),
                bootstrap=dict(path=str(bootstrap), sha256=sha(bootstrap)),
                native_build=proof['actual_native_build'], remap_proof=proof,
                unchanged_remap_sources=unchanged, cargo_policy_review=reviewed,
                cargo_recipe_files=old_policy['cargo_recipe_files'],
                cargo_source_commit_means='Reviewed recipe source pin; no Cargo binary identity or execution inferred.')


def candidate(q, prerequisite, compiled, old_spec, provider, provider_reference, remap,
              *, source, sysroot, read_json, read_bytes, sha):
    runtime = q.runtime
    revision = compiled['candidate_revision']
    require(prerequisite['candidate_revision'] == revision
            and prerequisite['source_identity'] == compiled['source_identity'], 'qualified compiler differs')
    require(provider['status'] == 'verified-readonly-provider-equivalence-not-installation'
            and provider['candidate_revision'] == revision, 'current distribution equivalence proof required')
    require(remap['source_commit'] == revision, 'current source policy required')
    components = []
    files, links = {}, {}
    for name, row in compiled['stage1'].items():
        if row['kind'] == 'file':
            value = (sysroot/name).lstat()
            require(stat.S_ISREG(value.st_mode) and sha(sysroot/name) == row['sha256'], 'current E2 byte differs')
            files[name] = dict(sha256=row['sha256'], size=value.st_size, mode=stat.S_IMODE(value.st_mode))
        else:
            require(row['kind'] == 'link' and name in runtime.SOURCE_ROOTS, 'unknown E2 source link')
            path = sysroot/name
            require(path.is_symlink() and path.resolve(strict=True) == source, 'current E2 source link differs')
            links[name] = dict(text=path.readlink().as_posix(), resolved_target=str(source),
                action='replace' if name == 'lib/rustlib/src/rust' else 'omit',
                reason='Ordinary reviewed standard source distribution; runtime does not expose compiler source.')
    components.append(dict(role='runtime', root=str(sysroot), destination='', files=files, links=links))
    for role in ['source', 'support']:
        component = copy.deepcopy(next(c for c in old_spec['components'] if c['role'] == role))
        if role == 'source':
            require(component['root'] == provider['source_distribution']['provider'], 'source provider root differs')
            require({n:r['sha256'] for n,r in component['files'].items()} ==
                    {n:r['sha256'] for n,r in provider['source_distribution']['provider_files'].items()}, 'source catalog differs')
            component['source_receipt_sha256'] = provider_reference['sha256']
        else:
            require(set(component['files']) == {'rust-objcopy'}
                    and component['files']['rust-objcopy']['sha256'] == provider['support']['file']['sha256'],
                    'support provider bytes differ')
        components.append(component)
    def probe(index, suffix):
        ref = compiled['command_history'][index]
        p = Path(ref['path']); child = read_json(p)
        require(sha(p) == ref['sha256'] and child['status'] == 'finished' and child['returncode'] == 0
                and child['command'] == [str(sysroot/'bin/rustc'), *suffix], 'actual E2 probe association differs')
        require(not read_bytes(p.parent/'stderr') and sha(p.parent/'stdout') == child['stdout_sha256'], 'actual E2 raw differs')
        return read_bytes(p.parent/'stdout').decode()
    spec = dict(schema_version=1, host=old_spec['host'], loader_policy=runtime.LOADER_POLICY,
        compiler=probe(17, ['-vV']), unstable_options=runtime.option_proof(probe(20, ['-Zhelp'])),
        provenance=dict(source_commit=revision, source_checkout=str(source),
            build_receipt_sha256=compiled['command_history'][16]['sha256'],
            qualification_receipt_sha256=prerequisite['hash_receipt_sha256'],
            bootstrap_sha256=remap['bootstrap']['sha256'], source_comparison_sha256=provider_reference['sha256']),
        components=components, loader={})
    for c in components:
        for name, row in c['files'].items():
            if c['role'] != 'source' and (name.endswith(('.dylib', '.so')) or row['mode'] & 0o111):
                output = c['destination']+'/'+name if c['destination'] else name
                spec['loader'][output] = macho(read_bytes(Path(c['root'])/name))
    runtime.identity_for(spec)
    return spec

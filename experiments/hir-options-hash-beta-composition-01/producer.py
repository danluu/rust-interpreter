"""Fail-closed association with the actual new build history's retained Cargo commands.

No filename glob, inherited B2 producer index, or timestamp is producer proof.
Future discovery supplies line coordinates; this module re-derives the argv and
ordinary rustc output names from those exact retained bytes. A stamped artifact
not covered by these native Rust output rules requires a reviewed successor;
the controller must not guess a build-script/native-archive producer.
"""
import re
import shlex
from pathlib import Path

from compose_sysroot import require, digest, check_file


def single(argv, option):
    values = []
    for index, word in enumerate(argv):
        if word == option:
            require(index + 1 < len(argv), 'missing compiler option value')
            values.append(argv[index + 1])
        elif word.startswith(option + '='):
            values.append(word[len(option) + 1:])
    require(len(values) == 1, 'require one compiler option: ' + option)
    return values[0]


def running_line(raw, coordinate):
    require(type(coordinate['line']) is int and coordinate['line'] > 0,
            'positive one-based producer line required')
    lines = raw.splitlines(keepends=True)
    require(coordinate['line'] <= len(lines), 'producer line absent')
    line = lines[coordinate['line'] - 1]
    require(digest(line) == coordinate['line_sha256'], 'producer raw line differs')
    text = line.decode('utf-8', errors='strict').rstrip('\r\n')
    match = re.fullmatch(r'\s*Running `(.+)`', text)
    require(match is not None, 'not an actual Cargo Running command')
    words = shlex.split(match[1], posix=True)
    environment = {}
    while words and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', words[0], re.S):
        name, value = words.pop(0).split('=', 1)
        require(name not in environment, 'duplicate producer environment key')
        environment[name] = value
    require(words and Path(words[0]).is_absolute(), 'absolute producer executable required')
    return dict(argv=words, environment=environment)


def rust_outputs(argv):
    """Only actual rustc --out-dir + crate-name + extra-filename outputs."""
    crate = single(argv, '--crate-name')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', crate), 'invalid producer crate')
    directory = Path(single(argv, '--out-dir'))
    require(directory.is_absolute() and '..' not in directory.parts,
            'noncanonical producer output directory')
    extra = []
    for index, word in enumerate(argv):
        value = argv[index + 1] if word == '-C' and index + 1 < len(argv) else word[2:] if word.startswith('-C') else ''
        if value.startswith('extra-filename='):
            extra.append(value.removeprefix('extra-filename='))
    require(len(extra) == 1 and re.fullmatch(r'-[a-zA-Z0-9]+', extra[0]),
            'one ordinary extra-filename required')
    stem = 'lib' + crate + extra[0]
    emits = single(argv, '--emit').split(',')
    require(all('=' not in value for value in emits), 'explicit emit destinations need separate proof')
    require('link' in emits and '--test' not in argv, 'check-only metadata/test executable is not a native private producer')
    crate_types = single(argv, '--crate-type').split(',')
    result = set()
    if 'metadata' in emits:
        result.add(str(directory / (stem + '.rmeta')))
    if 'link' in emits:
        for kind in crate_types:
            require(kind in ['lib', 'rlib', 'dylib', 'proc-macro', 'bin'],
                    'unsupported native Rust producer type')
            if kind in ['lib', 'rlib']:
                result.add(str(directory / (stem + '.rlib')))
            elif kind in ['dylib', 'proc-macro']:
                result.add(str(directory / (stem + '.dylib')))
    return result


def bootstrap_line(raw, coordinate, source):
    """Parse bootstrap's actual Cargo command, not invented per-rustc env."""
    lines = raw.splitlines(keepends=True)
    require(type(coordinate['line']) is int and 0 < coordinate['line'] <= len(lines), 'bootstrap line absent')
    line = lines[coordinate['line'] - 1]
    require(digest(line) == coordinate['line_sha256'], 'bootstrap raw command differs')
    text = line.decode('utf-8', errors='strict').rstrip('\r\n')
    require(text.startswith('running: '), 'not an actual bootstrap command')
    words = shlex.split(text.removeprefix('running: '))
    require(words[:4] == ['cd', str(source), '&&', 'env'], 'bootstrap command cwd/form differs')
    words = words[4:]
    removed, environment = [], {}
    while words and words[0] == '-u':
        require(len(words) >= 2 and re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', words[1]), 'invalid removed environment key')
        removed.append(words[1]); words = words[2:]
    require(len(removed) == len(set(removed)), 'duplicate removed environment key')
    while words and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*=.*', words[0], re.S):
        name, value = words.pop(0).split('=', 1)
        require(name not in environment, 'duplicate bootstrap environment key')
        environment[name] = value
    require(words and words[-1] == '(failure_mode=Exit)', 'unexpected bootstrap failure policy')
    words.pop()
    require(len(words) >= 2 and Path(words[0]).is_absolute() and words[1] in ['build', 'test', 'check'],
            'actual native Cargo command required')
    return dict(argv=words, environment=environment, removed=removed)


def mechanism(row, cargo, inherited, source):
    """Match the actual two-shim Cargo route and rustc.rs host/target split."""
    source = Path(source)
    host = 'aarch64-apple-darwin'
    d = source / 'build' / host / 'stage0'
    shim = str(source / 'build/bootstrap/debug/rustc')
    require(row['argv'][:2] == [shim, shim], 'actual bootstrap RUSTC_WRAPPER/RUSTC argv route differs')
    require(cargo['argv'][0] == str(d / 'bin/cargo'), 'Cargo provider differs from qualified D2')
    environment = dict(inherited)
    for key in cargo['removed']:
        environment.pop(key, None)
    environment.update(cargo['environment'])
    # Cargo may print crate-local additions, but may not replace these routes.
    for name, value in row['environment'].items():
        require(name not in environment or environment[name] == value or not name.startswith(('RUSTC', 'CFG_')),
                'crate-local environment changed compiler routing/identity')
        environment[name] = value
    required = dict(RUSTC=shim, RUSTC_WRAPPER=shim, RUSTC_REAL=str(d / 'bin/rustc'),
        RUSTC_SNAPSHOT=str(d / 'bin/rustc'), RUSTC_LIBDIR=str(d / 'lib'),
        RUSTC_SNAPSHOT_LIBDIR=str(d / 'lib'), RUSTC_STAGE='0',
        RUSTC_SYSROOT=str(source / 'build' / host / 'stage0-sysroot'),
        CARGO_TARGET_DIR=str(source / 'build' / host / 'stage1-rustc'),
        CARGO_BUILD_BUILD_DIR=str(source / 'build' / host / 'stage1-rustc'))
    require(all(environment.get(k) == v for k, v in required.items()), 'actual D2/bootstrap provider binding differs')
    require(not any(environment.get(k) for k in ['RUSTC_WRAPPER_REAL', 'RUSTC_FORCE_RUSTC_VERSION',
        'RUSTC_ADDITIONAL_SYSROOT_PATHS', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES']),
        'unadmitted compiler/loader override in actual producer')
    require('--sysroot' not in row['argv'] and not any(x.startswith('--sysroot=') for x in row['argv']),
            'producer supplies a separate sysroot override')
    targets = [value for i, word in enumerate(row['argv'][:-1]) if word == '--target' for value in [row['argv'][i + 1]]]
    targets += [word.removeprefix('--target=') for word in row['argv'] if word.startswith('--target=')]
    require(targets in [[], [host]], 'producer target route differs')
    # No target means rustc.rs chooses RUSTC_SNAPSHOT and its libdir. Both exact
    # alternatives above are D2; host flags remain in the raw inherited env.
    return environment


def validate(proof, composition, streams, revision):
    """streams contains qualified successful stages, never an unrelated build.

    Earlier native dependencies from `./x test` may be Fresh in the final build.
    Exact compiler output flags and the bound bootstrap route, not the outer
    stage's spelling, determine whether an entry is an actual native producer.
    """
    private = {row['source']: row for row in composition['private']}
    require(set(proof['private']) == set(private), 'producer proof omits private stamp entries')
    # Retain every printed Cargo command for this exact native build tree,
    # across all successful stages, including repeated printed invocations.
    # A chosen coordinate is not allowed to hide another observed mechanism.
    cargo_catalog = []
    for name, stream in sorted(streams.items()):
        for number, line in enumerate(stream['raw'].splitlines(keepends=True), 1):
            if not line.startswith(b'running: ') or b'CARGO_TARGET_DIR=' not in line:
                continue
            if composition['tree'].encode() not in line:
                continue
            coordinate = dict(stream=name, line=number, line_sha256=digest(line))
            parsed = bootstrap_line(stream['raw'], coordinate, composition['source'])
            if parsed['environment'].get('CARGO_TARGET_DIR') == composition['tree']:
                cargo_catalog.append(dict(command=coordinate, parsed=parsed,
                    child_receipt=stream['child_receipt'], stage_index=stream['stage_index']))
    require(cargo_catalog and proof['cargo_catalog'] == cargo_catalog,
            'complete actual native Cargo command catalog differs')
    commands = {}
    def actual(binding):
        coordinate, cargo_coordinate = binding['command'], binding['cargo_command']
        require(coordinate['stream'] in streams and cargo_coordinate['stream'] in streams,
                'producer command outside successful compiler history')
        one, outer = streams[coordinate['stream']], streams[cargo_coordinate['stream']]
        require(one['child_receipt'] == outer['child_receipt'], 'Cargo mechanism belongs to another child')
        row = running_line(one['raw'], coordinate)
        cargo = bootstrap_line(outer['raw'], cargo_coordinate, composition['source'])
        require(any(item['command'] == cargo_coordinate for item in cargo_catalog), 'unlisted actual Cargo mechanism')
        require(row == binding['parsed'] and cargo == binding['parsed_cargo'], 'actual producer/Cargo command differs')
        environment = mechanism(row, cargo, one['environment'], composition['source'])
        return row, environment
    for source, binding in proof['private'].items():
        coordinate = binding['command']
        key = (coordinate['stream'], coordinate['line'])
        row, environment = actual(binding)
        require(source in rust_outputs(row['argv']), 'stamp source is not this actual compiler output')
        file = private[source]['file']
        require(check_file(file) == file, 'private output changed after actual discovery')
        # Exact bootstrap source identity for compiler crates is retained on
        # the actual command, including the virtual remap namespaces.
        compiler_source = str(Path(composition['source']) / 'compiler') + '/'
        if any(word.endswith('.rs') and word.startswith((compiler_source, 'compiler/'))
               for word in row['argv']):
            env = environment
            for name, value in proof['compiler_environment'].items():
                require(env.get(name) == value, 'compiler source environment differs: ' + name)
            require(env.get('CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR') == '/rustc-dev/' + revision
                    and env.get('CFG_VIRTUAL_RUST_SOURCE_BASE_DIR') == '/rustc/' + revision,
                    'compiler source remapping differs')
        commands[key] = row
    consumer = proof['consumer']
    row, environment = actual(consumer)
    require(single(row['argv'], '--crate-name') == 'rustc_main',
            'actual rustc_main consumer required')
    pair = []
    for index, word in enumerate(row['argv']):
        if word == '--extern' and index + 1 < len(row['argv']):
            value = row['argv'][index + 1]
        elif word.startswith('--extern='):
            value = word.removeprefix('--extern=')
        else:
            continue
        if value.startswith('rustc_driver='):
            pair.append(value.removeprefix('rustc_driver='))
    require(pair == consumer['ordered_driver_pair'] and len(pair) == 2,
            'actual ordered driver dylib/rmeta extern pair differs')
    require(all(path in private for path in pair), 'consumer pair absent from complete stamp')
    require(pair[0].endswith('.dylib') and pair[1] == str(Path(pair[0]).with_suffix('.rmeta')),
            'consumer does not use matching dylib then rmeta')
    require(private[pair[0]]['file']['sha256'] == composition['runtime_driver']['sha256'],
            'native consumer driver differs from E2')
    return dict(private_entries=len(private), distinct_producers=len(commands),
                ordered_driver_destinations=[private[path]['destination'] for path in pair])

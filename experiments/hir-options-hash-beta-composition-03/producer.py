"""Fail-closed association with the actual new build history's retained Cargo commands.

No filename glob, inherited B2 producer index, or timestamp is producer proof.
Future discovery supplies line coordinates; this module re-derives the argv and
ordinary rustc output names from those exact retained bytes. A stamped artifact
not covered by these native Rust output rules requires a reviewed successor;
the controller must not guess a build-script/native-archive producer.
"""
import re
import json
import timing_context
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


def test_loader_paths(source):
    """Exact native-host test::prepare_cargo_test order with admitted CI LLVM."""
    root = Path(source) / 'build/aarch64-apple-darwin'
    return [str(root / 'stage0/lib'), str(root / 'ci-llvm/lib'),
            str(root / 'stage0-sysroot/lib/rustlib/aarch64-apple-darwin/lib')]


def loader_policy(row, cargo, inherited, source):
    # add_dylib_path chains the *bootstrap process* environment, not the
    # command's prior env; the admitted child has no inherited loader paths.
    require(not any(k.startswith(('DYLD_', 'LD_')) for k in inherited),
            'unadmitted inherited loader environment')
    require(not any(k.startswith(('DYLD_', 'LD_')) for k in row['environment']),
            'crate-local loader environment override')
    expected = ':'.join(test_loader_paths(source)) if cargo['argv'][1] == 'test' else None
    require(cargo['environment'].get('DYLD_LIBRARY_PATH') == expected,
            'test-only ordered bootstrap loader path differs')
    require(not any(k.startswith(('DYLD_', 'LD_')) and k != 'DYLD_LIBRARY_PATH'
                    for k in cargo['environment']), 'unadmitted Cargo loader override')
    return expected


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
    loader_policy(row, cargo, inherited, source)
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
        'RUSTC_ADDITIONAL_SYSROOT_PATHS', 'DYLD_FALLBACK_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES']),
        'unadmitted compiler/loader override in actual producer')
    require('--sysroot' not in row['argv'] and not any(x.startswith('--sysroot=') for x in row['argv']),
            'producer supplies a separate sysroot override')
    targets = [value for i, word in enumerate(row['argv'][:-1]) if word == '--target' for value in [row['argv'][i + 1]]]
    targets += [word.removeprefix('--target=') for word in row['argv'] if word.startswith('--target=')]
    require(targets in [[], [host]], 'producer target route differs')
    # No target means rustc.rs chooses RUSTC_SNAPSHOT and its libdir. Both exact
    # alternatives above are D2; host flags remain in the raw inherited env.
    return environment



def allowed_bootstrap_commands():
    return [
        ['./x', 'check', '--stage', '1', 'compiler/rustc_ast_lowering', '--jobs', '2', '-vv'],
        ['./x', 'test', '--stage', '1', 'compiler/rustc_ast_lowering', '--jobs', '2', '-vv'],
        ['./x', 'build', '--stage', '1', 'compiler/rustc', 'library', '--jobs', '2', '-vv'],
        ['./x', 'test', '--stage', '1', 'compiler/rustc_interface', '--jobs', '2', '-vv'],
        ['./x', 'build', '--stage', '1', 'src/tools/run-make-support', '--jobs', '2', '-vv'],
    ]


def native_emitter(cargo, step, source):
    """Exact Mode::Rustc routes from compile/check/test Step implementations.

    The test route prints before the same stream guard in render_tests.rs;
    it does not use compile::stream_cargo. Both remain separately source-bound.
    """
    source = Path(source); host = 'aarch64-apple-darwin'
    argv, env = cargo['argv'], cargo['environment']
    require(argv[0] == str(source / 'build' / host / 'stage0/bin/cargo'), 'unproved timed Cargo executable')
    require(argv[1] in ['build', 'check', 'test'], 'unproved timed Cargo mode')
    require(single(argv, '--target') == host
            and single(argv, '--manifest-path') == str(source / 'compiler/rustc/Cargo.toml'),
            'timed Cargo manifest/target route differs')
    tree = str(source / 'build' / host / 'stage1-rustc')
    require(env.get('CARGO_TARGET_DIR') == env.get('CARGO_BUILD_BUILD_DIR') == tree,
            'timed Cargo native output route differs')
    if argv[1] in ['build', 'check']:
        require(single(argv, '--message-format') == 'json-render-diagnostics', 'unknown Cargo stream format')
    else:
        require('--' in argv and '--format' in argv[argv.index('--') + 1:]
                and single(argv[argv.index('--') + 1:], '--format') == 'json', 'unknown test-renderer route')
        require(not any(x == '--message-format' or x.startswith('--message-format=') for x in argv[:argv.index('--')]),
                'unproved Cargo JSON test route')
    head = argv[:argv.index('--')] if '--' in argv else argv
    packages = []
    for i, word in enumerate(head):
        if word == '-p':
            require(i + 1 < len(head) and re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9-]*', head[i + 1]), 'invalid Cargo package selection')
            packages.append(head[i + 1])
        elif word.startswith(('-p', '--package', '--workspace', '--exclude')):
            raise ValueError('unproved Cargo package selection spelling')
    require(len(packages) == len(set(packages)), 'duplicate Cargo package selection')
    compiler = 'Compiler { stage: 0, host: ' + host + ', forced_compiler: false }'
    prefix = {
        'build': 'compile::Rustc { target: ' + host + ', build_compiler: ' + compiler + ', crates: ',
        'check': 'check::Rustc { check_kind: Check, build_compiler: CompilerForCheck { build_compiler: '
                 + compiler + ', rustc_rmeta_sysroot: None, std_rmeta_sysroot: None }, target: ' + host + ', crates: ',
        'test': 'test::Crate { build_compiler: ' + compiler + ', target: ' + host + ', mode: Rustc, crates: ',
    }[argv[1]]
    if step is not None:
        require(step.startswith(prefix) and step.endswith(' }'), 'unknown timed Cargo emitting Step/role')
        crates = json.loads(step[len(prefix):-2])
        require(isinstance(crates, list) and all(isinstance(name, str) and re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9-]*', name) for name in crates),
                'unproved timed Step crate selection')
        require(len(crates) == len(set(crates)), 'duplicate timed Step crate selection')
        require(packages == crates, 'timed Step/Cargo package selection mismatch')
    return 'test::Crate/run_cargo_test/render_tests::run_tests' if argv[1] == 'test' else (
        'compile::Rustc/run_cargo/stream_cargo' if argv[1] == 'build' else 'check::Rustc/run_cargo/stream_cargo')


def unambiguous_environment(row, candidates, source):
    """Every plausible same-child context must yield the same complete environment.

    stdout/stderr coordinates do not prove which bootstrap Cargo invocation
    enclosed a Running line. Reject ambiguity instead of inferring nesting.
    Compare all keys (including arbitrary env! inputs and provider settings),
    not just known RUSTC/CFG prefixes. Actual rustc argv is separately retained.
    """
    require(candidates, 'no plausible native Cargo context for actual producer')
    expected = None
    for candidate in candidates:
        environment = mechanism(row, candidate['cargo'], candidate['inherited'], source)
        if expected is None:
            expected = environment
        else:
            require(environment == expected,
                    'ambiguous same-child Cargo compiler environment')
    return expected


def actual_command(binding, cargo_catalog, streams, source):
    coordinate, cargo_coordinate = binding['command'], binding['cargo_command']
    require(coordinate['stream'] in streams and cargo_coordinate['stream'] in streams,
            'producer command outside successful compiler history')
    one, outer = streams[coordinate['stream']], streams[cargo_coordinate['stream']]
    require(one['child_receipt'] == outer['child_receipt'], 'Cargo mechanism belongs to another child')
    row = running_line(one['raw'], coordinate)
    cargo = bootstrap_line(outer['raw'], cargo_coordinate, source)
    selected = [item for item in cargo_catalog if item['command'] == cargo_coordinate]
    require(len(selected) == 1 and selected[0]['execution'] == 'real', 'selected Cargo context is not proved real')
    require(row == binding['parsed'] and cargo == binding['parsed_cargo'], 'actual producer/Cargo command differs')
    # The catalog is complete across both retained streams. A convenient
    # coordinate alone does not prove nesting or inherited source flags.
    plausible = [item for item in cargo_catalog if item['child_receipt'] == one['child_receipt'] and item['execution'] == 'real']
    candidates = []
    for item in plausible:
        context = streams[item['command']['stream']]
        require(context['environment'] == one['environment'],
                'same child has inconsistent inherited environment records')
        candidates.append(dict(cargo=item['parsed'], inherited=context['environment']))
    environment = unambiguous_environment(row, candidates, source)
    return row, environment


def validate(proof, composition, streams, revision, configuration):
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
            'complete printed native Cargo command catalog differs')
    classified, timings = [], {}
    for stream_name in sorted({item['command']['stream'] for item in cargo_catalog}):
        stream = streams[stream_name]
        require(stream['stream_kind'] == 'stdout', 'bootstrap printed Cargo command outside stdout')
        timing_context.configured(configuration, stream['outer_argv'], allowed_bootstrap_commands())
        entries = [item for item in cargo_catalog if item['command']['stream'] == stream_name]
        result = timing_context.classify(stream['raw'], entries,
            lambda cargo, step: native_emitter(cargo, step, composition['source']))
        classified.extend(result['commands']); timings[stream_name] = result
    require(proof['timing_contexts'] == timings, 'complete actual timing classification differs')
    cargo_catalog = classified
    commands = {}
    for source, binding in proof['private'].items():
        coordinate = binding['command']
        key = (coordinate['stream'], coordinate['line'])
        row, environment = actual_command(binding, cargo_catalog, streams, composition['source'])
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
    row, environment = actual_command(consumer, cargo_catalog, streams, composition['source'])
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

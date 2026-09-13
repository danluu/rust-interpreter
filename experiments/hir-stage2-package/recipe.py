"""Exact recipe environment and raw-hit checks, adapted from qualified replay2dcf."""
from pathlib import Path
import re
import shlex

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def recipe_environment(text, inherited, expected):
    """The final executed compiletest command, followed by run_make.rs's env edits."""
    SOURCE, HOST = Path(expected['source']), expected['host']
    BUILD, SYSROOT = SOURCE / 'build' / HOST, Path(expected['sysroot'])
    COMPILETEST, RUSTC = Path(expected['compiletest']), Path(expected['compiler'])
    STAGE0_LIB = BUILD / 'stage0/lib/rustlib' / HOST / 'lib'
    stage = str(expected['stage'])
    lines = [line for line in text.splitlines() if line.startswith('running: env ')
             and str(COMPILETEST) in line and '"--run-make-support-rlib"' in line]
    require(len(lines) == 1 and lines[0].endswith(' (failure_mode=Exit)'),
            'one final executed compiletest command required')
    tokens = shlex.split(lines[0][len('running: '):-len(' (failure_mode=Exit)')])
    require(tokens.pop(0) == 'env', 'compiletest env envelope changed')
    env = dict(inherited)
    while tokens[0] != str(COMPILETEST):
        value = tokens.pop(0)
        if value == '-u': env.pop(tokens.pop(0), None)
        else:
            require('=' in value, 'unknown compiletest env operation')
            key, value = value.split('=', 1); env[key] = value
    tokens.pop(0)
    boolean = {'--no-capture', '--optimize-tests', '--verbose', '--verbose-run-make-subprocess-output',
               '--with-std-remap-debuginfo', '--with-rustc-debug-assertions', '--with-std-debug-assertions',
               '--profiler-runtime', '--git-hash'}
    options, filters = {}, []
    while tokens:
        key = tokens.pop(0)
        if key in boolean: value = True
        elif key.startswith('--'):
            require(tokens, 'missing compiletest option value'); value = tokens.pop(0)
        else: filters.append(key); continue
        if key in options:
            require(key in {'--host-rustcflags', '--target-rustcflags'}, 'duplicate compiletest option')
        options.setdefault(key, []).append(value)
    one = lambda name: options[name][0]
    required_options = {'--stage': stage, '--suite': 'run-make', '--mode': 'run-make', '--host': HOST,
        '--target': HOST, '--rustc-path': str(RUSTC), '--src-root': str(SOURCE),
        '--build-root': str(SOURCE / 'build'), '--compile-lib-path': str(SYSROOT / 'lib'),
        '--run-lib-path': str(SYSROOT / 'lib/rustlib' / HOST / 'lib'), '--jobs': '2',
        '--stage0-rustc-path': str(BUILD / 'stage0/bin/rustc')}
    require(all(options.get(k) == [v] for k, v in required_options.items())
            and filters == ['hir-body-cache-capture'] and '--verbose-run-make-subprocess-output' in options
            and not any(k in options for k in ['--bless', '--target-linker', '--runner', '--remote-test-client']),
            'unexpected recipe route, filter, or execution option')
    require(env.get('RUSTC_BOOTSTRAP') == '1' and env.get('RUSTC_FORCE_RUSTC_VERSION') == 'compiletest'
            and 'CARGO' not in env, 'original compiletest environment differs')
    support = BUILD / 'bootstrap-tools' / HOST / 'release'
    require(one('--run-make-support-rlib') == str(support / 'librun_make_support.rlib')
        and Path(one('--run-make-support-rmeta')).is_relative_to(support / 'build/run_make_support'),
        'recipe support-library path escaped bootstrap output')
    base = env['DYLD_LIBRARY_PATH'].split(':')
    require(base == [str(Path(one('--run-make-support-rmeta')).parent)], 'unexpected base dylib route')
    env.update(LD_LIB_PATH_ENVVAR='DYLD_LIBRARY_PATH', DYLD_LIBRARY_PATH=':'.join([*base, str(STAGE0_LIB)]),
        HOST_RUSTC_DYLIB_PATH=one('--compile-lib-path'), TARGET_EXE_DYLIB_PATH=one('--run-lib-path'),
        TARGET=HOST, PYTHON=one('--python'), SOURCE_ROOT=str(SOURCE), BUILD_ROOT=str(BUILD),
        RUSTC=one('--rustc-path'), LLVM_COMPONENTS=one('--llvm-components'), __BOOTSTRAP_JOBS=one('--jobs'),
        CC=one('--cc'), CXX=one('--cxx'), AR=one('--ar'), CC_DEFAULT_FLAGS=one('--cflags'), CXX_DEFAULT_FLAGS=one('--cxxflags'))
    for key, option in {'RUSTDOC': '--rustdoc-path', 'NODE': '--nodejs', 'LLVM_FILECHECK': '--llvm-filecheck',
                        'LLVM_BIN_DIR': '--llvm-bin-dir'}.items():
        if option in options: env[key] = one(option)
    for key, option in {'__RMAKE_VERBOSE_SUBPROCESS_OUTPUT': '--verbose-run-make-subprocess-output',
        '__RUSTC_DEBUG_ASSERTIONS_ENABLED': '--with-rustc-debug-assertions',
        '__STD_DEBUG_ASSERTIONS_ENABLED': '--with-std-debug-assertions',
        '__STD_REMAP_DEBUGINFO_ENABLED': '--with-std-remap-debuginfo'}.items():
        env.pop(key, None)
        if option in options: env[key] = '1'
    env.pop('RUSTFLAGS', None)
    return dict(environment=env, original_compiletest_command=lines[0], options=options)

def checked_replay(text):
    """Use real recipe success plus raw compiler observations, without a libtest footer."""
    require('TRUNCATED' not in text, 'truncated output')
    hits = re.findall(r'(?m)^\[hir-body-reuse\][^\n]*$', text)
    require(hits, 'no actual verified cache hits in direct recipe output')
    names = set()
    for line in hits:
        match = re.fullmatch(r'\[hir-body-reuse\] ([a-z0-9_]+) hit cache_hits=1 '
            r'verify_tree=1 verify_journal=1 verify_poststate=1 S=(0|[1-9][0-9]*) E=(0|[1-9][0-9]*)', line)
        require(match is not None and 0 < int(match[2]) < int(match[3]) <= 0xFFFF_FF00,
                'malformed actual hit or invalid ItemLocalId interval')
        names.add(match[1])
    required = {'anchor', 'add', 'method', 'double', 'shadow', 'generic', 'conditional', 'array_index',
        'uninitialized', 'raw', 'arithmetic', 'literals', 'unsafe_block', 'flow', 'early', 'field', 'choose'}
    require(required <= names, 'complete recipe hit roles absent')
    for state in ['cold-tree-and-journal-after-stock-lowering', 'same-tree-and-journal-after-stock-lowering']:
        require('[hir-body-capture] anchor ' + state in text, 'capture history evidence absent')
    for code in ['E0308', 'E0382', 'E0080', 'unconditional_panic', 'unused_variables']:
        require(code in text, 'raw uncalled error/lint evidence absent')
    for label in ['empty', 'nonempty']:
        for mode in ['ordinary', 'capture', 'reuse']:
            for outcome in ['positive', 'negative']:
                require('-Cincremental=override-' + label + '-' + mode + '-' + outcome in text,
                        'version override control output absent')
    return dict(actual_verified_hits=len(hits), actual_hit_names=sorted(names),
                complete_unchanged_recipe_returned_successfully=True)

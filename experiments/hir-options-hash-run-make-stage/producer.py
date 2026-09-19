"""Actual bootstrap-tool producer route, adapted from reviewed B3 producer02.

RunMakeSupport is Mode::ToolBootstrap: raw stage0 sysroot and bootstrap-tools
output, as bound tool.rs/cargo.rs/session.rs specify. No future output is assumed.
"""
import hashlib
import re
import shlex
from pathlib import Path

def require(value,message):
    if not value:raise RuntimeError(message)
def digest(data):return hashlib.sha256(data).hexdigest()

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
        RUSTC_SYSROOT=str(d),
        CARGO_TARGET_DIR=str(source / 'build' / host / 'bootstrap-tools'),
        CARGO_BUILD_BUILD_DIR=str(source / 'build' / host / 'bootstrap-tools'))
    require(all(environment.get(k) == v for k, v in required.items()), 'actual D2/bootstrap provider binding differs')
    require(not any(environment.get(k) for k in ['RUSTC_WRAPPER_REAL', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTC_FORCE_RUSTC_VERSION',
        'RUSTC_ADDITIONAL_SYSROOT_PATHS', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES']),
        'unadmitted compiler/loader override in actual producer')
    require(not any(value for key,value in environment.items() if key.startswith(('LD_', 'DYLD_'))), 'unadmitted loader environment in actual support producer')
    require('--sysroot' not in row['argv'] and not any(x.startswith('--sysroot=') for x in row['argv']),
            'producer supplies a separate sysroot override')
    targets = [value for i, word in enumerate(row['argv'][:-1]) if word == '--target' for value in [row['argv'][i + 1]]]
    targets += [word.removeprefix('--target=') for word in row['argv'] if word.startswith('--target=')]
    require(targets in [[], [host]], 'producer target route differs')
    # No target means rustc.rs chooses RUSTC_SNAPSHOT and its libdir. Both exact
    # alternatives above are D2; host flags remain in the raw inherited env.
    return environment


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



"""Support-producer parsing, adapted from the reviewed B3 producer contract."""
import hashlib
import re
import shlex
from pathlib import Path

def require(value,message):
 if not value:raise ValueError(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()

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



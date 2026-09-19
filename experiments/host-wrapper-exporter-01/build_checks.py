"""Unchanged ordinary Cargo compiler/output validation bodies from qualified build02."""
import re
import shlex
from pathlib import Path

def require(ok,message):
    if not ok: raise RuntimeError(message)


def check_build_diagnostics(stderr):
    require(not any(text in stderr for text in (b'stripping debug info', b'SIGABRT',
            b'Library not loaded:', b'internal compiler error')), 'Cargo helper/strip/native compiler failure')


def cargo_compiles(stderr, binding, source_root, frozen_sources):
    result = []
    d = binding['build']['executable']['path']
    for line in stderr.decode().splitlines():
        match = re.fullmatch(r'\s*Running `(.*)`', line)
        if not match:
            continue
        argv = shlex.split(match[1])
        if '--crate-name' not in argv:
            continue
        require(argv.count(d) == 1, 'actual Cargo compiler is not exact D')
        at = argv.index(d); command = argv[at:]; prefix = argv[:at]
        if prefix[:1] == ['env']:
            prefix = prefix[1:]
        require(all('=' in word for word in prefix), 'unexpected compiler command prefix')
        require(all(flag in command for flag in binding['build_rustflags'])
                and sum(word.startswith('--sysroot') for word in command) == 1, 'actual D/B2/R compiler flags differ')
        require(not any('RUSTC_FORCE_RUSTC_VERSION=' in word or 'RUSTC_OVERRIDE_VERSION_STRING=' in word for word in argv),
                'compiler version override appeared')
        sources = [word for word in command if word.endswith('.rs')]
        require(len(sources) == 1, 'ambiguous actual compiler source')
        source = Path(sources[0]); source = source if source.is_absolute() else source_root / source
        source = str(source.resolve(strict=True))
        require(source in frozen_sources, 'Cargo compiled an unfrozen source')
        result.append(dict(command=command, environment_assignments=argv[:at], source=source))
    require({'rust_interp_mir_export', 'rust_interp_rustc_wrapper'} <=
            {row['command'][row['command'].index('--crate-name') + 1] for row in result}, 'both actual tool compiles required')
    return result
